# Vibe-Check Camera Data Pipeline Summary

This note captures how the legacy `vibe-check` codebase ingests NYC traffic camera data, writes it to storage, and drives downstream processing. Sources reviewed include the Firebase Functions implementation under `vibe-check/functions/src` and supporting project logs in `vibe-check/log`.

## Ingestion and Feature Extraction

- `processImageWithVision` wraps Google Cloud Vision, requesting object localization and labels before reducing the response into pedestrian, bike, and vehicle counts plus a 17-element feature vector that feeds the rest of the stack.

```188:305:/Users/gilraitses/vibe-check/functions/src/camera-processing.ts
export async function processImageWithVision(imageBuffer: Buffer): Promise<any> {
  // Cloud Vision OBJECT_LOCALIZATION + LABEL_DETECTION
  const [result] = await visionClient.annotateImage(request);
  const objectCounts = {
    pedestrian_count: objects.filter(obj => obj.name?.toLowerCase().includes('person')).length,
    bicycle_count: objects.filter(obj => obj.name?.toLowerCase().includes('bicycle')).length,
    vehicle_count: objects.filter(obj => obj.name?.toLowerCase().includes('car')).length,
    total_objects_detected: objects.length
  };
  const numerical_data = [
    Math.min(objectCounts.pedestrian_count, 5),
    Math.min(objectCounts.bicycle_count, 3),
    // ... existing code ...
    objectCounts.total_objects_detected
  ];
  return { numerical_data, cloud_vision_data: { ...objectCounts, safety_score } };
}
```

- The enhanced `/monitoring/camera-image/:cameraId` pipeline looks up camera metadata in Firestore, maps the entry to an NYC UUID, downloads the live frame, computes the feature vector above, and generates a “temperature” score through the adaptive monitoring engine.

## Database Encoding Paths

### Firestore

- Every analysis run writes an `analysisRecord` into `analyses`, updates the originating `monitoring_schedules` document, and optionally caches the response in Redis.

```752:789:/Users/gilraitses/vibe-check/functions/src/index.ts
const analysisRecord = { /* zone info, numerical_data, prediction, pipeline_status, ... */ };
await db.collection('analyses').add(analysisRecord);
await db.collection('monitoring_schedules').doc(cameraId).update({
  current_score: temperature_score,
  last_analysis_time: admin.firestore.FieldValue.serverTimestamp()
});
```

- Alert handling follows the same dual-write pattern: each violation alert becomes a Firestore document in `alerts` after routing through classification and notification delivery.

```251:279:/Users/gilraitses/vibe-check/functions/src/alertProcessor.ts
const alertRecord = {
  alert_id: uuidv4(),
  camera_id: violation.camera_id,
  violation_type: violation.violation_type,
  confidence: violation.confidence,
  classification,
  // ... existing code ...
};
await db.collection('alerts').doc(alertRecord.alert_id).set(alertRecord);
```

### BigQuery

- The ingestion layer mirrors each analysis into `vibecheck_analytics.zone_analyses` through `insertZoneAnalysis`, while separate helpers push predictions and violations into dedicated tables with JSON features persisted as text payloads.

```330:399:/Users/gilraitses/vibe-check/functions/src/bigquery.ts
export async function insertViolation(violation) {
  const row = { ...violation, timestamp, ml_features: JSON.stringify(violation.ml_features) };
  await bigquery.dataset(DATASET_ID).table('realtime_violations').insert(row);
}

export async function insertPrediction(prediction) {
  const row = { ...prediction, timestamp };
  await bigquery.dataset(DATASET_ID).table('traffic_predictions').insert(row);
}
```

- Alert events are copied to `vibecheck_analytics.alert_events` for cross-system auditing.

```271:274:/Users/gilraitses/vibe-check/functions/src/alertProcessor.ts
await bigquery.dataset('vibecheck_analytics').table('alert_events').insert([alertRecord]);
```

## Downstream Processing

- A scheduled Cloud Function (`trainBigQueryModels`) provisions analytic tables (`camera_metrics`, `violation_patterns`, `longitudinal_trends`, `ml_model_predictions`, `ml_model_registry`) and refreshes an ARIMA_PLUS model that forecasts temperature scores, logging metrics back to BigQuery for traceability.

```21:141:/Users/gilraitses/vibe-check/functions/src/bqTrainer.ts
export const trainBigQueryModels = functions.pubsub.schedule('every day 02:00').onRun(async () => {
  await createTables();
  await trainForecastModel();
});

const createModelSQL = `CREATE OR REPLACE MODEL \`${DATASET}.${modelId}\`
  OPTIONS(MODEL_TYPE='ARIMA_PLUS', TIME_SERIES_TIMESTAMP_COL='timestamp', TIME_SERIES_DATA_COL='temperature_score')
  AS SELECT timestamp, temperature_score FROM \`${DATASET}.${TABLES.cameraMetrics}\`
  WHERE temperature_score IS NOT NULL`;
```

- The codebase also ships additional utilities:
  - `trainARIMAPlusModel`, `trainCrimePredictionModel`, and `trainAnomalyDetectionModel` orchestrate further BigQuery ML experiments, though they depend on tables that currently appear sparsely populated.
  - `bigqueryRouteAnalytics.ts` records route-level metrics and queries ML forecasts for pedestrian routing decisions.
  - `redisService.ts` wraps Redis for caching analysis responses in five-minute buckets to reduce repeated Vision calls.

## Operational Notes from Project Logs

- Daily status entries (for example `log/2025-06-25.md`) assert that Firestore held 918 active `monitoring_schedules` documents and that 11 BigQuery tables were live with real data. The repository does not contain database exports, so those counts cannot be independently confirmed here, but the code paths above align with the described dual-write architecture.
- Several incident reports highlight earlier Firestore validation issues (e.g., missing `frame_url` fields) and emphasize the need for production credentials when invoking Cloud Vision or third-party notifications; those safeguards are still present in the current implementation.

## Takeaways for Pax

- The historical stack treated Firestore as the canonical operational store and BigQuery as the analytical lake. Pax should expect to ingest historical camera snapshots from Firestore/BigQuery exports, not from flat files alone.
- Reusing the feature vector format (17 numeric channels plus derived scores) will simplify migration because downstream analytics assume that schema.
- When rebuilding collectors, prioritize explicit fallbacks and error metadata: the legacy implementation recorded processing errors and pipeline step status alongside each analysis, which is valuable for validation.


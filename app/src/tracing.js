// Instrumentación OpenTelemetry. Se carga antes que la aplicación (node --require).
// Envía trazas y métricas por OTLP/HTTP al colector del APM (grafana/otel-lgtm).
const { NodeSDK, tracing } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');
const { OTLPMetricExporter } = require('@opentelemetry/exporter-metrics-otlp-http');
const {
  PeriodicExportingMetricReader,
  View,
  ExplicitBucketHistogramAggregation,
  InstrumentType,
} = require('@opentelemetry/sdk-metrics');
const { BatchSpanProcessor } = tracing;

// Cubetas finas para que los percentiles p50/p95/p99 calculados en Prometheus sean precisos.
const BUCKETS_MS = [1, 2, 3, 5, 7, 10, 15, 20, 30, 40, 50, 75, 100, 150, 200, 300, 400, 500,
  750, 1000, 1500, 2000, 3000, 5000, 7500, 10000];

const sdk = new NodeSDK({
  spanProcessors: [
    new BatchSpanProcessor(new OTLPTraceExporter(), {
      maxQueueSize: 20000,
      maxExportBatchSize: 1000,
      scheduledDelayMillis: 1000,
    }),
  ],
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter(),
    exportIntervalMillis: 5000,
  }),
  views: [
    new View({
      instrumentName: 'http.server.duration',
      instrumentType: InstrumentType.HISTOGRAM,
      aggregation: new ExplicitBucketHistogramAggregation(BUCKETS_MS),
    }),
  ],
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-fs': { enabled: false },
      '@opentelemetry/instrumentation-dns': { enabled: false },
      '@opentelemetry/instrumentation-net': { enabled: false },
      '@opentelemetry/instrumentation-http': {
        ignoreIncomingRequestHook: (req) => req.url === '/health',
      },
      '@opentelemetry/instrumentation-pg': { enhancedDatabaseReporting: false },
    }),
  ],
});

sdk.start();

const shutdown = () => sdk.shutdown().finally(() => process.exit(0));
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

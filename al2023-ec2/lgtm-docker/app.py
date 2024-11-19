import asyncio
import time
import random
from flask import Flask, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry._logs import set_logger_provider



from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
import logging
import requests
from functools import wraps


import logging
from flask import Flask, request
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# 공통 설정
endpoint = "http://localhost:4317"  # OpenTelemetry Collector 엔드포인트
resource = Resource.create({"service.name": "flask-demo-service"})


# Flask 애플리케이션 생성 및 인스트루먼테이션
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
LoggingInstrumentor().instrument(set_logging_format=True)
RequestsInstrumentor().instrument()

######################################################
# 트레이스 설정
trace_exporter = OTLPSpanExporter(endpoint=endpoint)
trace_provider = TracerProvider(resource=resource)
trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)


############################################################
# 로그 설정
log_exporter = OTLPLogExporter(endpoint=endpoint)
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
set_logger_provider(logger_provider)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
logger.addHandler(handler)
logger.info("Logging Started")

##########################################
# 메트릭 설정
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=endpoint)
)
metric_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(metric_provider)
meter = metrics.get_meter(__name__)

# HTTP 요청 횟수를 기록하는 카운터
request_counter = meter.create_counter(
    name="http_request_count",
    description="Number of HTTP requests",
    unit="1"
)

# 요청 처리 시간을 기록하는 히스토그램
request_duration = meter.create_histogram(
    name="http_request_duration",
    description="Duration of HTTP requests",
    unit="milliseconds"
)

@app.get("/health")
def health():
    request_counter.add(1, {"endpoint": "/health"})
    return {"message":"I'm healthy"}

@app.get("/")
def read_root():
    request_counter.add(1, {"endpoint": "/"})
    logging.info("Hello World")
    return {"Hello": "World"}

@app.get("/io_task")
def io_task():
    request_counter.add(1, {"endpoint": "/io_task"})
    time.sleep(1)
    logging.error("io task")
    return "IO bound task finish!"

@app.get("/cpu_task")
def cpu_task():
    request_counter.add(1, {"endpoint": "/cpu_task"})
    for i in range(1000):
        n = i*i*i
    #logging.error("cpu task")
    logging.info("cpu task")
    return "CPU bound task finish!"

@app.get("/random_status")
def random_status():
    request_counter.add(1, {"endpoint": "/random_status"})
    logging.error("random status")
    return {"path": "/random_status"}

@app.get("/random_sleep")
def random_sleep():
    request_counter.add(1, {"endpoint": "/random_sleep"})
    time.sleep(random.randint(0, 5))
    #logging.error("random sleep")
    logging.info("random sleep")
    return {"path": "/random_sleep"}

@app.get("/error_test")
def error_test():
    request_counter.add(1, {"endpoint": "/error_test"})
    logging.error("got error!!!!")
    raise ValueError("value error")

# 비동기 작업을 위한 데코레이터
def async_action(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapped

# 비동기 작업 시뮬레이션 함수
async def async_operation(name):
    with tracer.start_as_current_span(f"async_{name}"):
        await asyncio.sleep(random.uniform(0.1, 0.5))
        logger.info(f"Async operation {name} completed")

# 외부 API 호출 시뮬레이션 함수
def external_api_call(url):
    with tracer.start_as_current_span("external_api_call"):
        response = requests.get(url)
        logger.info(f"External API call to {url} completed with status {response.status_code}")
        return response.json()

# 복잡한 작업을 수행하는 엔드포인트
@app.route('/complex-operation')
@async_action
async def complex_operation():
    request_counter.add(1, {"endpoint": "/complex_operation"})
    start_time = time.time()

    with tracer.start_as_current_span("complex_operation"):
        logger.info("Starting complex operation")
        
        # 데이터베이스 쿼리 시뮬레이션
        with tracer.start_as_current_span("database_query"):
            await asyncio.sleep(random.uniform(0.1, 0.3))
            logger.info("Database query completed")
        
        # 데이터 처리 시뮬레이션
        with tracer.start_as_current_span("processing"):
            await asyncio.sleep(random.uniform(0.2, 0.4))
            logger.info("Data processing completed")
        
        # 여러 비동기 작업 동시 실행
        await asyncio.gather(
            async_operation("task1"),
            async_operation("task2"),
            async_operation("task3")
        )
        
        # 외부 API 호출
        external_data = external_api_call("https://jsonplaceholder.typicode.com/todos/1")
        
        # 최종 계산 시뮬레이션
        with tracer.start_as_current_span("final_computation"):
            await asyncio.sleep(random.uniform(0.1, 0.2))
            logger.info("Final computation completed")
        
        # 처리 시간 측정 (예시)
        with tracer.start_as_current_span("request_duration"):
            duration = (time.time() - start_time) * 1000  # 밀리초로 변환
            request_duration.record(duration, {"endpoint": "/complex_operation"})

        return {"message": "Complex operation completed", "external_data": external_data}

# 메인 실행 부분
if __name__ == '__main__':
    logger.info("Application started")
    app.run(debug=False, port=5000, host="0.0.0.0")
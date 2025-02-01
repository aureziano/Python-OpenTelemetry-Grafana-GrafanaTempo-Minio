from flask import Flask
from flasgger import Swagger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

import threading
import time

app = Flask(__name__)

# Configuração do Swagger
app.config['SWAGGER'] = {
    'title': 'API de Exemplo com OpenTelemetry',
    'uiversion': 3,
    'specs_route': '/apidocs/',
    'specs': [
        {
            'endpoint': 'apispec',
            'route': '/apispec.json',
            'rule_filter': lambda rule: True,
            'model_filter': lambda tag: True,
        }
    ]
}
swagger = Swagger(app)

# Configuração do OpenTelemetry
resource = Resource(attributes={
    SERVICE_NAME: "python-api"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

otlp_exporter = OTLPSpanExporter(
    endpoint="http://otel-collector:4318/v1/traces",
    timeout=30,
    headers={"Content-Type": "application/json"}
)

span_processor = BatchSpanProcessor(
    otlp_exporter,
    max_export_batch_size=512,
    schedule_delay_millis=5000
)

trace.get_tracer_provider().add_span_processor(span_processor)

console_exporter = ConsoleSpanExporter()
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(console_exporter))

FlaskInstrumentor().instrument_app(app)

@app.route('/')
def hello():
    """
    Endpoint de Saudação
    ---
    responses:
      200:
        description: Retorna uma mensagem de saudação
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: Hello, World!
    """
    with tracer.start_as_current_span("hello-operation"):
        return "Hello, World!"

def generate_periodic_traces():
    while True:
        with tracer.start_as_current_span("periodic-trace"):
            print("Generating periodic trace")
        time.sleep(5)

@app.route('/start-periodic-traces')
def start_periodic_traces():
    """
    Inicia geração periódica de traces
    ---
    responses:
      200:
        description: Confirmação de início da geração de traces
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: Periodic trace generation started
    """
    thread = threading.Thread(target=generate_periodic_traces)
    thread.start()
    return "Periodic trace generation started"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

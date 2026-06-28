import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from predictor import DeepfakePredictor
from routes import router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
log = logging.getLogger('deepfake-service')

app = FastAPI(
    title='Deepfake Detection Service',
    version='1.0',
    description='Standalone microservice for image, video, and website URL deepfake detection.',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)


@app.on_event('startup')
def startup_event():
    try:
        predictor = DeepfakePredictor()
        app.state.predictor = predictor
        log.info('Deepfake Detection Service Started')
        log.info('Running on: http://localhost:8001')
        log.info('Models Loaded')
        log.info('✔ EfficientNet-B0')
        log.info('✔ Swin Transformer')
        log.info('✔ Xception')
        log.info('✔ ResNet-34')
        log.info('Ready for Prediction')
    except Exception as e:
        log.error(f'Failed to initialize predictor: {str(e)}', exc_info=True)
        raise


@app.get('/')
def root():
    return {'message': 'Deepfake Detection Service is running.'}

from unittest.mock import patch

import pytest
from onnxruntime import InferenceSession

from facefusion import face_detector, state_manager
from facefusion.inference_manager import INFERENCE_POOL_SET, get_inference_pool


@pytest.fixture(scope = 'module', autouse = True)
def before_all() -> None:
	state_manager.init_item('execution_device_ids', [ 0 ])
	state_manager.init_item('execution_providers', [ 'cpu' ])
	state_manager.init_item('download_providers', [ 'github' ])
	state_manager.init_item('face_detector_model', 'retinaface')
	face_detector.pre_check()


def test_get_inference_pool() -> None:
	model_names = [ 'retinaface' ]
	_, model_source_set = face_detector.collect_model_downloads()

	with patch('facefusion.inference_manager.detect_app_context', return_value = 'cli'):
		get_inference_pool('facefusion.face_detector', model_names, model_source_set)

		assert isinstance(INFERENCE_POOL_SET.get('cli').get('facefusion.face_detector.retinaface.0.cpu').get('retinaface'), InferenceSession)

	with patch('facefusion.inference_manager.detect_app_context', return_value = 'ui'):
		get_inference_pool('facefusion.face_detector', model_names, model_source_set)

		assert isinstance(INFERENCE_POOL_SET.get('cli').get('facefusion.face_detector.retinaface.0.cpu').get('retinaface'), InferenceSession)

	assert INFERENCE_POOL_SET.get('cli').get('facefusion.face_detector.retinaface.0.cpu').get('retinaface') == INFERENCE_POOL_SET.get('ui').get('facefusion.face_detector.retinaface.0.cpu').get('retinaface')

import threading
from typing import Callable, Optional, Tuple

import gradio

from facefusion import process_manager
from facefusion.filesystem import is_file, is_image, is_video

_ACTIVE_OUTPUT_PATH : Optional[str] = None
_IS_BACKGROUND_RUNNING = False
_JUST_FINISHED = False
_STOP_REQUESTED = False
_PENDING_JOB_RUNNER_DROPDOWN : Optional[gradio.Dropdown] = None
_JOB_THREAD : Optional[threading.Thread] = None


def set_active_output_path(output_path : Optional[str]) -> None:
	global _ACTIVE_OUTPUT_PATH

	_ACTIVE_OUTPUT_PATH = output_path


def clear_active_output_path() -> None:
	global _ACTIVE_OUTPUT_PATH

	_ACTIVE_OUTPUT_PATH = None


def request_stop() -> None:
	global _STOP_REQUESTED
	global _JUST_FINISHED

	_STOP_REQUESTED = True
	_JUST_FINISHED = False
	clear_active_output_path()


def set_pending_job_runner_dropdown(dropdown : gradio.Dropdown) -> None:
	global _PENDING_JOB_RUNNER_DROPDOWN

	_PENDING_JOB_RUNNER_DROPDOWN = dropdown


def is_background_running() -> bool:
	return _IS_BACKGROUND_RUNNING or process_manager.is_processing()


def run_in_background(target : Callable[..., None], *args : object, output_path : Optional[str] = None) -> bool:
	global _IS_BACKGROUND_RUNNING
	global _JUST_FINISHED
	global _STOP_REQUESTED
	global _JOB_THREAD

	if is_background_running():
		return False

	_JUST_FINISHED = False
	_STOP_REQUESTED = False
	_IS_BACKGROUND_RUNNING = True
	set_active_output_path(output_path)

	def wrapper() -> None:
		global _IS_BACKGROUND_RUNNING
		global _JUST_FINISHED

		try:
			target(*args)
		finally:
			_IS_BACKGROUND_RUNNING = False
			if not _STOP_REQUESTED:
				_JUST_FINISHED = True

	_JOB_THREAD = threading.Thread(target = wrapper, daemon = True)
	_JOB_THREAD.start()
	return True


def get_processing_buttons() -> Tuple[gradio.Button, gradio.Button]:
	if is_background_running():
		return gradio.Button(visible = False), gradio.Button(visible = True)
	return gradio.Button(visible = True), gradio.Button(visible = False)


def build_output_updates(output_path : str) -> Tuple[gradio.Image, gradio.Video]:
	if is_image(output_path):
		return gradio.Image(value = output_path, visible = True), gradio.Video(value = None, visible = False)
	if is_video(output_path):
		return gradio.Image(value = None, visible = False), gradio.Video(value = output_path, visible = True)
	return gradio.Image(value = None, visible = False), gradio.Video(value = None, visible = False)


def poll_instant_runner_state() -> Tuple[gradio.Button, gradio.Button, gradio.Image, gradio.Video]:
	global _JUST_FINISHED

	if is_background_running():
		return gradio.Button(visible = False), gradio.Button(visible = True), gradio.skip(), gradio.skip()

	if _JUST_FINISHED:
		output_path = _ACTIVE_OUTPUT_PATH
		_JUST_FINISHED = False
		clear_active_output_path()

		if output_path and is_file(output_path):
			output_image, output_video = build_output_updates(output_path)
			return gradio.Button(visible = True), gradio.Button(visible = False), output_image, output_video

		return gradio.Button(visible = True), gradio.Button(visible = False), gradio.skip(), gradio.skip()

	return gradio.skip(), gradio.skip(), gradio.skip(), gradio.skip()


def restore_instant_runner_on_load() -> Tuple[gradio.Button, gradio.Button, gradio.Image, gradio.Video]:
	if is_background_running():
		return gradio.Button(visible = False), gradio.Button(visible = True), gradio.skip(), gradio.skip()
	return poll_instant_runner_state()


def poll_job_runner_state() -> Tuple[gradio.Button, gradio.Button, gradio.Dropdown]:
	global _JUST_FINISHED
	global _PENDING_JOB_RUNNER_DROPDOWN

	if is_background_running():
		return gradio.Button(visible = False), gradio.Button(visible = True), gradio.skip()

	if _JUST_FINISHED:
		_JUST_FINISHED = False
		clear_active_output_path()
		start_button, stop_button = get_processing_buttons()

		if _PENDING_JOB_RUNNER_DROPDOWN:
			pending_dropdown = _PENDING_JOB_RUNNER_DROPDOWN
			_PENDING_JOB_RUNNER_DROPDOWN = None
			return start_button, stop_button, pending_dropdown

		return start_button, stop_button, gradio.skip()

	return gradio.skip(), gradio.skip(), gradio.skip()


def restore_job_runner_on_load() -> Tuple[gradio.Button, gradio.Button, gradio.Dropdown]:
	if is_background_running():
		return gradio.Button(visible = False), gradio.Button(visible = True), gradio.skip()
	return poll_job_runner_state()

from time import sleep
from typing import Optional, Tuple

import gradio

from facefusion import process_manager, state_manager, translator
from facefusion.args import collect_step_args
from facefusion.core import process_step
from facefusion.filesystem import is_directory
from facefusion.jobs import job_helper, job_manager, job_runner, job_store
from facefusion.temp_helper import clear_temp_directory
from facefusion.types import Args, UiWorkflow
from facefusion.uis.core import get_ui_component
from facefusion.uis.ui_helper import suggest_output_path
from facefusion.uis import ui_process_helper

INSTANT_RUNNER_WRAPPER : Optional[gradio.Row] = None
INSTANT_RUNNER_START_BUTTON : Optional[gradio.Button] = None
INSTANT_RUNNER_STOP_BUTTON : Optional[gradio.Button] = None
INSTANT_RUNNER_CLEAR_BUTTON : Optional[gradio.Button] = None
INSTANT_RUNNER_TIMER : Optional[gradio.Timer] = None


def render() -> None:
	global INSTANT_RUNNER_WRAPPER
	global INSTANT_RUNNER_START_BUTTON
	global INSTANT_RUNNER_STOP_BUTTON
	global INSTANT_RUNNER_CLEAR_BUTTON
	global INSTANT_RUNNER_TIMER

	if job_manager.init_jobs(state_manager.get_item('jobs_path')):
		is_instant_runner = state_manager.get_item('ui_workflow') == 'instant_runner'

		with gradio.Row(visible = is_instant_runner) as INSTANT_RUNNER_WRAPPER:
			INSTANT_RUNNER_START_BUTTON = gradio.Button(
				value = translator.get('uis.start_button'),
				variant = 'primary',
				size = 'sm'
			)
			INSTANT_RUNNER_STOP_BUTTON = gradio.Button(
				value = translator.get('uis.stop_button'),
				variant = 'primary',
				size = 'sm',
				visible = False
			)
			INSTANT_RUNNER_CLEAR_BUTTON = gradio.Button(
				value = translator.get('uis.clear_button'),
				size = 'sm'
			)
		INSTANT_RUNNER_TIMER = gradio.Timer(0.5, active = True)


def listen() -> None:
	output_image = get_ui_component('output_image')
	output_video = get_ui_component('output_video')
	ui_workflow_dropdown = get_ui_component('ui_workflow_dropdown')

	if output_image and output_video and INSTANT_RUNNER_TIMER:
		INSTANT_RUNNER_START_BUTTON.click(start, outputs = [ INSTANT_RUNNER_START_BUTTON, INSTANT_RUNNER_STOP_BUTTON ])
		INSTANT_RUNNER_START_BUTTON.click(run, outputs = [ INSTANT_RUNNER_START_BUTTON, INSTANT_RUNNER_STOP_BUTTON, output_image, output_video ])
		INSTANT_RUNNER_STOP_BUTTON.click(stop, outputs = [ INSTANT_RUNNER_START_BUTTON, INSTANT_RUNNER_STOP_BUTTON, output_image, output_video ])
		INSTANT_RUNNER_CLEAR_BUTTON.click(clear, outputs = [ output_image, output_video ])
		INSTANT_RUNNER_TIMER.tick(ui_process_helper.poll_instant_runner_state, outputs = [ INSTANT_RUNNER_START_BUTTON, INSTANT_RUNNER_STOP_BUTTON, output_image, output_video ])
	if ui_workflow_dropdown:
		ui_workflow_dropdown.change(remote_update, inputs = ui_workflow_dropdown, outputs = INSTANT_RUNNER_WRAPPER)


def remote_update(ui_workflow : UiWorkflow) -> gradio.Row:
	is_instant_runner = ui_workflow == 'instant_runner'

	return gradio.Row(visible = is_instant_runner)


def start() -> Tuple[gradio.Button, gradio.Button]:
	while not ui_process_helper.is_background_running():
		sleep(0.5)
	return gradio.Button(visible = False), gradio.Button(visible = True)


def run() -> Tuple[gradio.Button, gradio.Button, gradio.Image, gradio.Video]:
	if ui_process_helper.is_background_running():
		return gradio.Button(visible = False), gradio.Button(visible = True), gradio.Image(visible = False), gradio.Video(visible = False)
	step_args = collect_step_args()
	output_path = step_args.get('output_path')

	if is_directory(step_args.get('output_path')):
		step_args['output_path'] = suggest_output_path(step_args.get('output_path'), state_manager.get_item('target_path'))
	if job_manager.init_jobs(state_manager.get_item('jobs_path')):
		ui_process_helper.run_in_background(run_job, step_args, output_path, output_path = step_args.get('output_path'))
	return gradio.Button(visible = False), gradio.Button(visible = True), gradio.Image(visible = False), gradio.Video(visible = False)


def run_job(step_args : Args, output_path : str) -> None:
	create_and_run_job(step_args)
	state_manager.set_item('output_path', output_path)


def create_and_run_job(step_args : Args) -> bool:
	job_id = job_helper.suggest_job_id('ui')

	for key in job_store.get_job_keys():
		state_manager.sync_item(key) #type:ignore[arg-type]

	return job_manager.create_job(job_id) and job_manager.add_step(job_id, step_args) and job_manager.submit_job(job_id) and job_runner.run_job(job_id, process_step)


def stop() -> Tuple[gradio.Button, gradio.Button, gradio.Image, gradio.Video]:
	process_manager.stop()
	ui_process_helper.clear_active_output_path()
	return gradio.Button(visible = True), gradio.Button(visible = False), gradio.Image(value = None), gradio.Video(value = None)


def clear() -> Tuple[gradio.Image, gradio.Video]:
	while ui_process_helper.is_background_running():
		sleep(0.5)
	if state_manager.get_item('target_path'):
		clear_temp_directory(state_manager.get_item('target_path'))
	return gradio.Image(value = None), gradio.Video(value = None)

"""FastAPI Browser Use API routes."""
import os
import sys
parent_dir = os.path.dirname(os.path.abspath(__file__))
up_dir = parent_dir
for i in range(3):
    sys.path.append(up_dir)
    up_dir = os.path.dirname(up_dir)
import utils as u

import json
import os
import subprocess
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError
from enum import Enum
import random

from ...metrics import get_metrics_collector
from ...server_logging import get_logger
from ..utils import get_a_trace_with_img, get_oss_client, save_trace_in_oss, list_traces, get_traces_from_oss

browser_router_v = APIRouter(prefix="/browser_v", tags=["browser_v"])
logger = get_logger(__name__)
metrics_collector = get_metrics_collector()

import visual.utils as u
from visual.rollout.browser_agent import BrowserAgent
from visual.llm_service.ais_qwen import KevinAISQwen

class ModeEnum(str, Enum):
    SOM = 'som'
    VISUAL = 'visual'

class BrowserAgentRequest(BaseModel):
    question: str
    base_url: str
    api_key: str
    model_name: str
    temperature: float = 0.3
    enable_memory: bool = False
    browser_port: str = "9111"
    user_data_dir: str = "/tmp/chrome-debug/0000"
    headless: bool = True
    window_width: int = 1280
    window_height: int = 1100
    extract_base_url: str = ""
    extract_api_key: str = ""
    extract_model_name: str = ""
    extract_temperature: float = 0.3
    return_trace: bool = False
    save_trace: bool = True
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_endpoint: str = ""
    oss_bucket_name: str = ""
    trace_dir_name: str = ""
    trace_file_name: str = ""
    max_steps: int = 100
    mode: ModeEnum = ModeEnum.SOM
    use_inner_chrome: bool = False
    google_api_key: str = ""
    google_search_engine_id: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.extract_base_url == "":
            self.extract_base_url = self.base_url
        if self.extract_api_key == "":
            self.extract_api_key = self.api_key
        if self.extract_model_name == "":
            self.extract_model_name = self.model_name
        if self.trace_dir_name == "":
            self.trace_dir_name = f"{datetime.now().strftime('%Y%m%d')}_default"
        if self.trace_file_name == "":
            random_number = random.randrange(100000)
            self.trace_file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_default_{random_number:05d}"


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def run_chrome_debug_mode(browser_port, user_data_dir, headless):
    browser_locate = "/usr/bin/google-chrome"
    try:
        command = [
            browser_locate,
            f"--remote-debugging-port={browser_port}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={user_data_dir}",
            "--no-sandbox",
            # "--headless",  # 启用无头模式
            # "--disable-gpu",  # 禁用 GPU 加速（可选）
            # "--window-size=1920,1080"  # 设置窗口大小（可选）
        ]
        if headless:
            command.append("--headless")
        process = subprocess.Popen(command)
    except Exception as e:
        print(e)
        browser_locate = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        command = [
            browser_locate,
            f"--remote-debugging-port={browser_port}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={user_data_dir}",
            "--no-sandbox",
            # "--headless",  # 启用无头模式
            # "--disable-gpu",  # 禁用 GPU 加速（可选）
            # "--window-size=1920,1080"  # 设置窗口大小（可选）
        ]
        if headless:
            command.append("--headless")
        process = subprocess.Popen(command)
    return browser_locate, process


async def process_browser_request(
    browser_request: BrowserAgentRequest, request_id: str = Depends(get_request_id)
):
    try:
        logger.info(f"[{request_id}] Processing browser agentic search")

        question = browser_request.question
        base_url = browser_request.base_url
        api_key = browser_request.api_key
        model_name = browser_request.model_name
        temperature = browser_request.temperature
        enable_memory = browser_request.temperature
        browser_port = browser_request.browser_port
        user_data_dir = browser_request.user_data_dir
        headless = browser_request.headless
        window_width = browser_request.window_width
        window_height = browser_request.window_height
        extract_base_url = browser_request.extract_base_url
        extract_api_key = browser_request.extract_api_key
        extract_model_name = browser_request.extract_model_name
        extract_temperature = browser_request.extract_temperature
        return_trace = browser_request.return_trace
        save_trace = browser_request.save_trace
        oss_access_key_id = browser_request.oss_access_key_id
        oss_access_key_secret = browser_request.oss_access_key_secret
        oss_endpoint = browser_request.oss_endpoint
        oss_bucket_name = browser_request.oss_bucket_name
        trace_dir_name = browser_request.trace_dir_name
        trace_file_name = browser_request.trace_file_name
        max_steps = browser_request.max_steps
        mode = browser_request.mode
        use_inner_chrome = browser_request.use_inner_chrome
        google_api_key = browser_request.google_api_key
        google_search_engine_id = browser_request.google_search_engine_id   

        kq_config = {
            'api_key': api_key,
            'model': model_name,
            'base_url': base_url,
            'temperature': temperature,
            'max_tokens': 4096,
        }

        kq = KevinAISQwen(kq_config)

        config = {
            'llm_request': kq.infer,
            'max_step': 30,
            'start_url': 'http://www.baidu.com',
            # 'mode': 'offline',
            'mode': 'online',
            'main_path': f'{u.get_nas()}/gui_dataset/playwright/',
        }
        ba = BrowserAgent(config)
        answers = ba.forward(question)

       
        oss_res = {"success": False}
        if save_trace:
            oss_client=get_oss_client(oss_access_key_id, oss_access_key_secret, oss_endpoint, oss_bucket_name, True)
            if oss_client._initialized:
                trace_dict = {"question": question, "agent_answer": answers}
                trace_prefix="ml001/browser_agent/traces/"
                dict_key = os.path.join(trace_prefix,trace_dir_name,trace_file_name+".json")
                result = oss_client.upload_data(trace_dict, dict_key)
            logger.info(f"oss_res: {oss_res}")
        
    except Exception as e:
        logger.error(f"[{request_id}] Error processing browser agentic search: {e}")

@browser_router_v.post("/browser_use_background_v")
async def agentic_browser_background_endpoint(
    background_tasks: BackgroundTasks, 
    browser_request: BrowserAgentRequest, 
    request_id: str = Depends(get_request_id)
):
    background_tasks.add_task(process_browser_request, browser_request,request_id)
    return {"message": "Request received and processing in background", "request_id": request_id,"pod_name":os.getenv('POD_NAME')}


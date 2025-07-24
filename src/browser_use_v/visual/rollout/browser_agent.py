import os
import sys
parent_dir = os.path.dirname(os.path.abspath(__file__))
up_dir = parent_dir
for i in range(3):
    sys.path.append(up_dir)
    up_dir = os.path.dirname(up_dir)
from kutils import DEBUG, INFO, WARN, ERROR
import visual.utils as u
from tqdm import tqdm
from PIL import Image
import io
from playwright.async_api import async_playwright
from dataset.multimodel_mind2web.prompt_parser import sys_prompt
from dataset.multimodel_mind2web.prompt_parser import prompt_bbox_250714 as prompt_f
from dataset.multimodel_mind2web.prompt_parser import parse_response_bbox_250714 as parse_response
from dataset.dataset_utils import draw_eval
from llm_service.ais_qwen import KevinAISQwen
from server_logging import get_logger
logger = get_logger(__name__)

async def pw_click(page, screenshot_width, screenshot_height, x, y):
    await page.set_viewport_size({"width": screenshot_width, "height": screenshot_height})
    await page.mouse.move(x, y)
    await page.mouse.click(x, y)

async def pw_type(page, screenshot_width, screenshot_height, x, y, text):
    await page.set_viewport_size({"width": screenshot_width, "height": screenshot_height})
    await page.mouse.move(x, y)
    await page.mouse.click(x, y)
    await page.keyboard.type(text)
    await page.keyboard.press('Enter')

async def pw_scroll(page, screenshot_height, dir):
    await page.mouse.wheel(0, screenshot_height)

async def pw_goto(page, url):
    await page.goto(url)

async def pw_back(page):
    can_go_back = await page.evaluate("window.history.length > 1")
    if can_go_back:
        await page.go_back()
    else:
        await page.close()

class BrowserAgent():
    def __init__(self, config):
        self.llm_request = config['llm_request']
        self.mode = config['mode']
        self.main_path = config['main_path']
        self.max_step = config['max_step']
        self.start_url = config['start_url']

    async def execute_action(self, page, context, action_info, img_size):
        w, h = img_size
        pred_action_history = action_info['pred_action_history']
        pred_action_description = action_info['pred_action_description']
        pred_action = action_info['pred_action']
        pred_action_type = action_info['pred_action_type']
        pred_bbox = action_info['pred_bbox']
        pred_type_value = action_info['pred_type_value']
        pred_click_point = action_info['pred_click_point']

        if pred_action_type == 'CLICK':
            await pw_click(page, w, h, *pred_click_point)
        elif pred_action_type == 'TYPE':
            await pw_type(page, w, h, *pred_click_point, pred_type_value)
        elif pred_action_type == 'SELECT':
            await pw_click(page, w, h, *pred_click_point)
        elif pred_action_type == 'SCROLL':
            await pw_scroll(page, h, pred_type_value)
        elif pred_action_type == 'GOTO':
            await pw_goto(page, pred_type_value)
        elif pred_action_type == 'BACK':
            await pw_back(page)

        if page in context.pages:
            await page.wait_for_timeout(3000)

    def infer(self, task, action_desc_history, img):
        response = self.llm_request(sys_prompt, prompt_f.format(task, action_desc_history), img)
        action_info = parse_response(response)
        action_info['raw'] = response
        return action_info

    async def forward(self, task):
        self.p = await async_playwright().start()
        self.browser = await self.p.chromium.launch()
        await self.browser.new_page()

        folder_name = task.replace(' ', '_').replace('?', '')[:20]
        task_path = f'{self.main_path}/{folder_name}/'
        ori_img_path = f'{task_path}/ori_img/'
        pred_img_path = f'{task_path}/pred_img/'
        actions_file = f'{task_path}/actions.json'

        if self.mode == 'offline':
            u.mkdir(self.main_path)
            u.mkdir(ori_img_path)
            u.mkdir(task_path)
            u.mkdir(pred_img_path)

        context = self.browser.contexts[0]
        # context = self.p.chromium.launch_persistent_context(
        #     user_data_dir=f'{self.main_path}/user_data/',
        #     headless=False
        # )
        curr_page = context.pages[-1]
        await curr_page.goto(self.start_url)

        i_step = 0
        pred_action_type = ''
        tabs = {}
        answers = {}
        action_desc_histories = []
        while pred_action_type != 'FINISH':
            logger.info(i_step)
            pages = context.pages
            n_tabs = len(pages)
            curr_page = pages[-1]
            for page in pages:
                title = await page.title()
                if i_step not in tabs.keys(): tabs[i_step] = []
                tabs[i_step].append(title)

            img_bytes = await curr_page.screenshot()
            if not isinstance(img_bytes, bytes): continue
            img_io = io.BytesIO(img_bytes)
            img = Image.open(img_io)
            action_info = self.infer(task, action_desc_histories, img)
            answers[i_step] = action_info
            answers[i_step]['img_bytes'] = img_bytes
            pred_action_history = action_info['pred_action_history']
            pred_action_description = action_info['pred_action_description']
            pred_action = action_info['pred_action']
            logger.info(pred_action)
            pred_action_type = action_info['pred_action_type']
            pred_bbox = action_info['pred_bbox']
            pred_type_value = action_info['pred_type_value']
            pred_click_point = action_info['pred_click_point']

            if self.mode == 'offline':
                ori_file = f'{ori_img_path}/ori_{i_step}.png'
                img.save(ori_file)
                u.write_json(actions_file, answers)
                pred_file = f'{pred_img_path}/pred_{i_step}.png'
                draw_eval(img, pred_click_point, task, '', pred_action, '', pred_action_description, pred_file)

            if pred_action_type == 'FINISH': return pred_type_value
            await self.execute_action(curr_page, context, action_info, img.size)

            i_step += 1
            if i_step > self.max_step: return ''

            action_desc_histories.append(pred_action_description)
            logger.info(action_desc_histories)
            
        logger.info('End')
        self.browser.close()
        self.p.stop()
        return answers 

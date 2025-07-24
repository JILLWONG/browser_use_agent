import os
import sys
parent_dir = os.path.dirname(os.path.abspath(__file__))
up_dir = parent_dir
for i in range(3):
    sys.path.append(up_dir)
    up_dir = os.path.dirname(up_dir)
from kutils import DEBUG, INFO, WARN, ERROR
import utils as u
import os
import PIL
from PIL import Image
import re

def expand_box(box, pixels=10):
    x_min, y_min, x_max, y_max = box
    x_min_expanded = x_min - pixels
    y_min_expanded = y_min - pixels
    x_max_expanded = x_max + pixels
    y_max_expanded = y_max + pixels
    return [x_min_expanded, y_min_expanded, x_max_expanded, y_max_expanded]

def draw_eval(gt_img_file, 
              pred_click_point, task, 
              gt_action, pred_action, 
              gt_action_desc, pred_action_desc, 
              save_file):

    def wrap_lines(s, n):
        lines = s.split('\n')
        res = []
        for line in lines:
            while len(line) > n:
                res.append(line[:n])
                line = line[n:]
            res.append(line)
        return '\n'.join(res)

    if isinstance(gt_img_file, PIL.PngImagePlugin.PngImageFile):
        img = gt_img_file
    else:
        img = Image.open(gt_img_file)
    res_img = img.copy()
    w, h = res_img.size
    res_img = u.draw_point(res_img, *pred_click_point, True, color='blue')
    fontsize = 16
    n_word_a_line = int(w / fontsize - 3)

    content = \
f'''task: {task}
gt_action: {gt_action}
pred_action: {pred_action}
gt_action_desc: {gt_action_desc}
pred_action_desc: {pred_action_desc}'''

    content = wrap_lines(content, n_word_a_line)
    res_img = u.add_text_bottom(res_img, content, font_size=fontsize)
    res_img.save(save_file)

def find2(s):
    pattern = r'\[\s*(\d+)\s*,\s*(\d+)\s*\]'

    match = re.search(pattern, s)
    if match:
        numbers = list(map(int, match.groups()))
        return numbers
    else:
        return [0, 0]

def find4(s):
    pattern = r'\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*'

    match = re.search(pattern, s)
    if match:
        numbers = list(map(int, match.groups()))
        return numbers
    else:
        return [0, 0, 0, 0]

def get_output_model_name(model_name):
    if '/checkpoint-' in model_name: model_name = model_name.replace('/checkpoint-', '_sft_')
    if '/global_step_' in model_name: model_name = model_name.replace('/global_step_', '_grpo_')
    if '/actor/huggingface/' in model_name: model_name = model_name.replace('/actor/huggingface/', '')
    if '/actor/huggingface' in model_name: model_name = model_name.replace('/actor/huggingface', '')
    if 'SCOT' in model_name: model_name = model_name[model_name.find('SCOT'):]
    output_model_name = model_name.replace('Qwen2.5-VL-7B-Instruct_grpo', 'DGRPO')
    output_model_name = output_model_name.replace('Qwen2.5-VL-7B-Instruct-SCOT', 'SCOT')
    return output_model_name

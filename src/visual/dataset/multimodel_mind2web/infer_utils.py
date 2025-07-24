import os
import sys
parent_dir = os.path.dirname(os.path.abspath(__file__))
up_dir = parent_dir
for i in range(3):
    sys.path.append(up_dir)
    up_dir = os.path.dirname(up_dir)
from kutils import DEBUG, INFO, WARN, ERROR
import utils as u
import json

def parse_type(pred_action):
    try:
        if pred_action.startswith('click'):
            pred_action_type = 'CLICK'
            pred_type_value = ''
        elif pred_action.startswith('select'):
            pred_action_type = 'SELECT'
            pred_type_value = pred_action.split('content=')[1].split("'")[1]
        elif pred_action.startswith('type'):
            pred_action_type = 'TYPE'
            pred_type_value = pred_action.split('content=')[1].split("'")[1]
        elif pred_action.startswith('goto'):
            pred_action_type = 'GOTO'
            pred_type_value = pred_action.split('url=')[1].split("'")[1]
        elif pred_action.startswith('scroll'):
            pred_action_type = 'SCROLL'
            pred_type_value = pred_action.split('direction=')[1].split("'")[1]
        elif pred_action.startswith('back'):
            pred_action_type = 'BACK'
            pred_type_value = ''
        elif pred_action.startswith('wait'):
            pred_action_type = 'WAIT'
            pred_type_value = ''
        elif pred_action.startswith('finish'):
            pred_action_type = 'FINISH'
            pred_type_value = pred_action.split('answer=')[1].split("'")[1]
        else:
            pred_action_type = 'UNKNOWN'
            pred_type_value = ''
    except:
        pred_action_type = 'UNKNOWN'
        pred_type_value = ''
    return pred_action_type, pred_type_value

def map_to_actions(action_type, gt_bbox, value = ''):
    if action_type == "CLICK":
        return f"click(start_box='<|box_start|>{json.dumps(gt_bbox)}<|box_end|>')"
    elif action_type == "TYPE":
        return f"type(content='{value}', start_box='<|box_start|>{json.dumps(gt_bbox)}<|box_end|>')"
    elif action_type == "SELECT":
        return f"select(content='{value}', start_box='<|box_start|>{json.dumps(gt_bbox)}<|box_end|>')"
    else:
        return "# Unknown action" 

def map_gt_action(operation, coordinates, value = ''):
    coordinates = json.dumps(coordinates)
    if 'CLICK' == operation:
        return f"click(start_box='<|box_start|>{coordinates})<|box_end|>')"
    elif 'TYPE' in operation:
        return f"type(content='{value}', start_box='<|box_start|>{coordinates}<|box_end|>')"
    elif 'SELECT' in operation:
        return f"select(content='{value}', start_box='<|box_start|>{coordinates}<|box_end|>')"
    else:
        return f"click(start_box='<|box_start|>{coordinates}<|box_end|>')"

def map_action_desc_history(action_history):
    for i, action in enumerate(action_history):
        if '-> CLICK' in action:
            content = u.extract_text(action, ']  ', ' -> CLICK')[0]
            click_type = u.extract_text(action, '[', ']')[0]
            if content:
                content = f'"{content}" was clicked'
            else:
                content = f'<{click_type}> was clicked'
            content = content.replace('', '')
            action_history[i] = content
        elif '-> TYPE' in action:
            content = u.extract_text(action, 'TYPE: ', None)
            content = f'"{content}" was typed'
            content = content.replace('', '')
            action_history[i] = content
        elif '-> SELECT' in action:
            content = u.extract_text(action, ']  ', ' -> SELECT')[0] 
            select_content = u.extract_text(action, ' -> SELECT: ', None)[0]
            content = f'{select_content} was selected in {content}'
            content = content.replace('', '')
            action_history[i] = content
        else:
            action_history[i] = action
    return action_history

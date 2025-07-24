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
import pandas as pd
import json
import io
import requests
from openai import OpenAI

class KevinAISQwen():
    def __init__(self, config):
        self.model = config['model']
        self.temperature = config['temperature']
        self.max_tokens = config['max_tokens']
        self.client = OpenAI(
            api_key = config['api_key'],
            base_url = config['base_url'],
        )

    def infer(self, system, prompt, pil_img):
        messages = \
        [
            {
                'role': 'system', 
                'content': system
            }, 
            {
                'role': 'user', 
                'content': [
                    {
                        'type': 'text', 
                        'text': prompt
                    }, 
                    {
                        'type': 'image_url', 
                        'image_url': { 
                            'url': 'data:imagepng;base64,' 
                        }
                    }
                ]
            }
        ]

        image_base64 = u.pil_image_to_base64(pil_img)
        messages[1]['content'][1]['image_url']['url'] += image_base64

        response = self.client.chat.completions.create(
            model = self.model,
            messages = messages,
            temperature = self.temperature,
            max_tokens = self.max_tokens,
        )
        response = response.choices[0].message.content
        return response


'''
Utilities for intepreting application deployments based on (OpenAPI) descriptions
of "things" (i.e., WebAssembly services/functions on devices) and executing
their instructions.
'''

from dataclasses import dataclass
from math import prod

import cv2
from flask import jsonify, send_file
import numpy as np
import requests

import wasm_utils.wasm_utils as wu


WASM_MEM_IMG_SHAPE = (480, 640, 3)

class ProgramCounterExceeded(Exception):
    '''Raised when a deployment sequence is exceeded.'''

class RequestFailed(Exception):
    '''Raised when a chained request to a thing fails.'''


@dataclass
class Deployment:
    '''Describing a sequence of instructions to be executed in (some) order.'''
    instructions: list
    program_counter: int = 0

    def _next_target(self):
        '''
        Choose the next instruction's target and increment internal state to
        prepare for the next call.
        '''
        target = self.instructions[self.program_counter]['to']
        # Update the sequence ready for next call to this deployment.
        self.program_counter += 1
        return target

    def call_chain(self, func_result, func_out_media_type, func_out_schema):
        '''
        Call a sequence of functions in order, passing the result of each to the
        next.

        Return the result of the recursive call chain or the local result which
        starts unwinding the chain.
        '''

        # From the WebAssembly function's execution, parse result into the type
        # that needs to be used as argument for next call in sequence.
        parsed_result = parse_func_result(func_result, func_out_media_type, func_out_schema)

        # Select whether to forward the result to next node (deepening the call
        # chain) or return it to caller (respond).
        target = self._next_target()
        sub_request_is_needed = target is not None

        if sub_request_is_needed:
            # Call next func in sequence based on its OpenAPI description.
            target_path, target_path_obj = list(target['paths'].items())[0]

            target_url = target['servers'][0]['url'].rstrip("/") + '/' + target_path.lstrip("/")

            # Request to next node.
            # NOTE: This makes a blocking call.
            sub_response = None
            # Fill in the parameters according to call method.
            if 'post' in target_path_obj:
                sub_response = request_to(target_url, func_out_media_type, parsed_result)
            else:
                raise NotImplementedError('Only POST is supported but was not found in target endpoint description.')

            # TODO: handle different response codes based on OpenAPI description.
            if sub_response.status_code != 200:
                raise RequestFailed(f'Bad status code {sub_response.status_code}')

            # FIXME: This is changed here in order to have the return type of
            # the whole chain be the same as return type of the last sequence in
            # the chain e.g. 
            #   Actor -> (None: Img) -> (Img: Int)
            # unravels as:
            #   Actor <- (None: Int) <- (Img: Int)
            func_out_media_type = sub_response.headers['Content-Type']

        # Return the result back to caller, BEGINNING the unwinding of the
        # recursive requests.
        if func_out_media_type == 'application/octet-stream':
            # TODO: Technically this should just return the bytes but figuring
            # that out seems too much of a hassle right now...
            return jsonify({ "result": parsed_result })
        else:
            raise NotImplementedError(f'bug: media type unhandled "{func_out_media_type}"')
     
def parse_func_result(func_result, expected_media_type, expected_schema):
    '''
    Interpret the result of a function call based on the function's OpenAPI
    description.
    '''
    # DEMO: This is how the Camera service is invoked (no input).
    if expected_media_type == 'application/json':
        # TODO: For other than 'null' JSON, parse object from func_result (which
        # might be a (fat)pointer to Wasm memory).
        response_obj = None
    # DEMO: This is how the ML service is sent an image.
    elif expected_media_type == 'image/jpeg':
        # Read the constant sized image from memory.
        # FIXME Assuming there is this function that gives the buffer address
        # found in the module.
        img_address = wu.run_function('get_img_ptr', b'')
        # FIXME Assuming the buffer size is according to this constant
        # shape.
        img_bytes, err = wu.read_from_memory(img_address, prod(WASM_MEM_IMG_SHAPE), to_list=True)
        if err:
            raise RuntimeError(f'Could not read image from memory: {err}')
        # Store raw bytes for now.
        response_obj = img_bytes
    # DEMO: This how the Camera service receives back the classification result.
    elif expected_media_type == 'application/octet-stream':
        response_obj = func_result
    else:
        raise NotImplementedError(f'Unsupported response media type {expected_media_type}')

    return response_obj

def request_to(url, media_type, payload):
    """
    Make a (sub or 'recursive') request to a URL selecting the placing of
    payload from media type.

    :return Response from `requests.post`
    """
    # List of key-path-mode -tuples for reading files on request.
    files = []
    data = None
    headers = {}
    if media_type == 'application/json' or \
        media_type == 'application/octet-stream':
        # HACK
        headers = { "Content-Type": media_type }
        data = payload
    elif media_type == 'image/jpeg':
        TEMP_IMAGE_PATH = 'temp_image.jpg'
        # NOTE: 'payload' at this point expected to be raw bytes read from
        # memory.
        img = np.array(payload).reshape(WASM_MEM_IMG_SHAPE)
        cv2.imwrite(TEMP_IMAGE_PATH, img)
        # TODO: Is this 'data' key hardcoded into ML-path and should it
        # instead be in an OpenAPI doc?
        files.append(("data", TEMP_IMAGE_PATH, "rb"))
    else:
        raise NotImplementedError(f'bug: media type unhandled "{media_type}"')

    files = { key: open(path, mode) for (key, path, mode) in files }

    return requests.post(
        url,
        timeout=60,
        data=data,
        files=files,
        headers=headers,
    )
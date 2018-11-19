
BASE_AUTH_URL = 'https://login.ubuntu.com'
API_V2_URL = BASE_AUTH_URL + '/api/v2'
API_TOKEN_DISCHARGE = BASE_AUTH_URL + '/tokens/discharge'
API_TOKEN_REFRESH = BASE_AUTH_URL + '/tokens/refresh'


class UbuntuSSOClient(object):


    def __init__(self , base_url=None):
        if not base_url:
            self.base_url = BASE_AUTH_URL

    def get_header(self):
        return {'User-Aget': 'ua-client v.', 'Accept': 'application/json',
                'Content-Type': 'appllication/json'}

    def requestDischargeMacaroon(self):
        

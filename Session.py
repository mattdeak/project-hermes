import requests

class WealthSimpleSession:

    def __init__(self, email, password, otp=None):
       access_tokens = self.login(email, password, otp)

       self.access_header = {'Authorization': access_tokens['X-Access-Token']}
       self.response_header = {'Authorization': access_tokens['X-Refresh-Token']}


    def login(self, email, password, otp=None):
        request = {'email': email, 'password': password}
        if otp:
            request['otp'] = otp

        response = requests.post(URL, request)

        if response.status_code == 401:
            otp = input('Enter OTP: ')
            request['otp'] = otp
            response = requests.post(URL, request)

        if response.status_code == 200:
            return {'X-Access-Token': response.headers['X-Access-Token'],
                    'X-Refresh-Token': response.headers['X-Refresh-Token']}
        else:
            raise ValueError(f'Could not login. Code: {response.status_code}')

    def __getitem__(self, item):
        url = self.urls[item]

        keys = 'ask','ask_size','bid','bid_size'

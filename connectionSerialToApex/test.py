import requests
import urllib3
urllib3.disable_warnings()

url = "https://oracleapex.com/ords/eggxperience/register/insert?microcontroler_id=1&sensor_id=3&value=12"

r = requests.get(url, verify=False, timeout=10)
print(r.status_code)
print(r.text)

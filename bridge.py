from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

APEX_BASE_URL = "https://apex.oracle.com/ords/eggxperience/register/insert"

@app.route('/send', methods=['GET'])
def relay():
    sensor_id = request.args.get("sensor_id")
    value = request.args.get("value")

    if sensor_id is None or value is None:
        return jsonify({"error": "faltan parámetros sensor_id o value"}), 400

    apex_url = f"{APEX_BASE_URL}?sensor_id={sensor_id}&value={value}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15)",
        "Accept": "*/*",
        "Connection": "keep-alive"
    }

    try:
        apex_response = requests.get(apex_url, headers=headers, timeout=30)

        return jsonify({
            "status": "OK",
            "sent_to": apex_url,
            "apex_status": apex_response.status_code,
            "apex_response": apex_response.text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("Relay iniciado en http://127.0.0.1:8080/send")
    app.run(host="0.0.0.0", port=8080)

import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

ORG_NAME = "sfdx_demo"
ORGS = []


class FakeMetaCI(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        length = int(self.headers.get("content-length", 0))
        self.send_header("Content-type", "application/json")
        body = self.rfile.read(length)
        if body:
            jsn = json.loads(body.decode("utf-8"))
            print(jsn.keys())
            if jsn["org_name"] == "release":
                print("RETURNING EMPTY LIST")
                return {}
        self.end_headers()
        self.wfile.write(ORGS.pop(0).encode(encoding="utf_8"))
        print("RETURNING ORG CONFIG. ", len(ORGS), "left")

        # get_org_json(ORG_NAME)

    def do_GET(self):
        return self.do_POST()


def get_org_json(orgname):
    subprocess.run(
        "sfdx force:org:create -f orgs/dev.json -w 120 -n --durationdays 1 -a sfdx_demo adminEmail=pprescod@salesforce.com",
        shell=True,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    subprocess.run(
        "cci org import sfdx_demo sfdx_demo",
        shell=True,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )

    out = subprocess.run(
        f"cci org info {orgname} --json",
        shell=True,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    json_ish = out.stdout
    bracket = json_ish.find("{")
    json_str = json_ish[bracket:]
    js = json.loads(json_str)

    out = subprocess.run(
        "sfdx force:org:display --json --verbose -u sfdx_demo",
        shell=True,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    json_ish = out.stdout
    bracket = json_ish.find("{")
    json_str = json_ish[bracket:]
    jsn = json.loads(json_str)
    js["sfdx_auth_url"] = jsn["result"]["sfdxAuthUrl"]
    print("Org Ready", len(ORGS) + 1)
    return json.dumps(js)


def run(server_class=HTTPServer, handler_class=FakeMetaCI):
    ORGS.append(get_org_json(ORG_NAME))
    global JSON_STR
    server_address = ("", 8001)
    httpd = server_class(server_address, handler_class)
    print("Server Ready")
    threading.Thread(target=org_pool_thread, daemon=True).start()
    httpd.serve_forever()


def org_pool_thread():
    orgs = ORGS
    while True:
        if len(orgs) < 5:
            orgs.append(get_org_json(ORG_NAME))

        time.sleep(1)


run()

from flask import Flask, request, Response
import os
import requests
import pickle as pk
import shutil
import json
from multiprocessing import Pool

app = Flask(__name__)


slack_access_token = os.environ.get("slack_access_token")
client_id = os.environ.get("client_id")

def download_file(url, file_id, channel_id, comment, user_id):
	r = requests.get(url, headers={'Authorization': 'Bearer {}'.format(slack_access_token)})
	data = r.content
	imgur_upload_url = "https://api.imgur.com/3/image"
	headers = {'Authorization': 'Client-ID {}'.format(client_id), "content-type": "multipart/form-data"}
	r = requests.post(imgur_upload_url, headers=headers, data=data)
	try:
		link = r.json()['data']['link']
	except KeyError:
		link = "Failed"
	print(link)
	print("---Deleting File---")
	slack_file_delete = "https://slack.com/api/files.delete?token={}&file={}"
	resp = requests.post(slack_file_delete.format(slack_access_token, file_id))
	if not resp.json()['ok']:
		print("Not able to delete file")
	try:
		hook_headers = {"Authorization": "Bearer {}".format(slack_access_token), "Content-Type": "application/json; charset=utf-8"}
		message_data = json.dumps({"channel": channel_id, "text": "Posted by <@{}>\n{}\n{}".format(user_id, comment, link)})
		post_url = "https://slack.com/api/chat.postMessage"
		link_post = requests.post(post_url, headers=hook_headers, data=message_data)
		print(link_post.json())
	except Exception as err:
		print("Error : "+err)


pool = Pool(processes=10)

@app.route('/app',methods=['GET','POST'])
def hello():
	json_data = request.json
	try:
		challenge = json_data['challenge']
		return challenge
	except KeyError:
		try:
			print(json_data['event']['file']['id'])
			file_id = json_data['event']['file']['id']
			file_info = requests.get("https://slack.com/api/files.info?token={}&file={}".format(slack_access_token, file_id))
			file_data = file_info.json()
			channel_id = file_data['file']['channels'][0]
			user_id = file_data['file']['user']
			try:
				comment = file_data['file']['initial_comment']['comment']
			except KeyError:
				comment = ''
			# print(file_data)
			if file_data['file']['size']/(1024**2) > 20:
				raise Exception("File too large (> 20MB)")
			file_permalink = file_data['file']['url_private_download']
			i = pool.apply_async(download_file, [file_permalink, file_id, channel_id, comment, user_id])
		except Exception as err:
			print("Error:- " + err)
		finally:
			return ("ok", 200, {'Access-Control-Allow-Origin': '*'})


if __name__ == '__main__':
	port = int(os.environ.get("PORT", 5000))  # the app is deployed on heroku
	app.run(host='0.0.0.0', port=port, debug=True)

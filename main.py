#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect, url_for
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip
from moviepy.video.tools.subtitles import SubtitlesClip
import os
import srt
import speech_recognition as sr
import datetime
from pydub import AudioSegment

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
	os.makedirs(UPLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def index():
	if request.method == 'POST':
		if 'file' not in request.files: return redirect(request.url)
		file = request.files['file']
		if file.filename == '': return redirect(request.url)
		if file and file.filename.endswith('.mp4'):
			filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
			file.save(filepath)
			return redirect(url_for('editor', filename=file.filename))
	return '''
	<!doctype html>
	<title>Upload new Video</title>
	<div style=\"position:relative;border: 2px solid black;padding: 5px;mar    gin: 0 auto;display:block;\">
	<h1>Upload MP4 File</h1>
	<form method=post enctype=multipart/form-data>
	<input type=file name=file>
	<input type=submit value=Upload>
	</form>
	</div>
	'''

@app.route('/edit', methods=['GET', 'POST'])
def editor():
	filename = request.args.get('filename')
	if request.method == 'POST':
		subtitles_printed = edit_video(filename)
		return subtitles_printed
	return '''
	<!doctype html>
	<title>Edit Video</title>
	<div style=\"position:relative;border: 2px solid black;padding: 5px;margin: 0 auto;display:block;\">
	<h1>Click to convert to MP3</h1>
	<form method=post enctype=multipart/form-data>
	<button type="submit" name="edit">Edit</button>
	</form>
	</div>
	'''

def generate_subtitles(text, total_duration):
	words_per_subtitle = 4
	words = text.split()
	subtitles = []
	num_subtitles = len(words) // words_per_subtitle + (1 if len(words) % words_per_subtitle else 0)
	subtitle_duration = total_duration / num_subtitles
	for i in range(num_subtitles):
		start_index = i * words_per_subtitle
		end_index = start_index + words_per_subtitle
		subtitle_text = ' '.join(words[start_index:end_index])
		start_time = datetime.timedelta(seconds=i * subtitle_duration)
		end_time = datetime.timedelta(seconds=(i + 1) * subtitle_duration)
		subtitles.append(srt.Subtitle(index=i + 1, start=start_time, end=end_time, content=subtitle_text))
	return subtitles

def edit_video(filename):
	video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
	audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.mp4', '.mp3'))
	wav_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.mp4', '.wav'))
	subtitle_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.mp4', '.srt'))
	
	clip = VideoFileClip(video_path)
	clip.audio.write_audiofile(audio_path)
	sound = AudioSegment.from_mp3(audio_path)
	sound.export(wav_audio_path, format="wav")

	r = sr.Recognizer()
	with sr.AudioFile(wav_audio_path) as source:
		audio = r.record(source)
	
	subtitles = []
	try:
		text = r.recognize_google(audio)
		subtitles = generate_subtitles(text, clip.duration)
		srt_content = srt.compose(subtitles)
		with open(subtitle_path, 'w') as f:
			f.write(srt_content)
	except (sr.UnknownValueError, sr.RequestError) as e:
		print("Error processing speech recognition:", e)

	def subtitle_generator(txt):
		main_clip = TextClip(txt, font='Arial', fontsize=64, color='white')
		shadow_clip = TextClip(txt, font='Arial', fontsize=64, color='black').set_position(("center", "center"), relative=True).margin(left=2, top=2, opacity=0)
		return CompositeVideoClip([shadow_clip, main_clip])

	subtitle_clip = SubtitlesClip(subtitle_path, subtitle_generator) if subtitles else None
	video = VideoFileClip(video_path)
	if subtitle_clip:
		vertical_position = video.size[1] * 2 / 3  # 2/3 from the top
		subtitle_clip = subtitle_clip.set_position(("center", vertical_position))
		video = CompositeVideoClip([video, subtitle_clip])
	else:
		print("No subtitles to overlay.")

	video_with_subtitles_path = os.path.join(app.config['UPLOAD_FOLDER'], 'subtitled_' + filename)
	video.write_videofile(video_with_subtitles_path, codec='libx264')
	return srt_content

if __name__ == "__main__":
	app.run(debug=True)

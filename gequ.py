import requests

def get_song_info(song_id):
    url = f'https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg?songid={song_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://y.qq.com'
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        song_name = data['data'][0]['songname']
        album_cover = data['data'][0]['album']['mid']
        return song_name, album_cover
    else:
        return None, None

# 示例获取歌曲信息
song_id = '你的歌曲ID'
song_name, album_cover = get_song_info(song_id)
print(f"Song: {song_name}")
print(f"Cover: {album_cover}")

import asyncio, subprocess
import imageio_ffmpeg
from pathlib import Path
from mutagen.id3 import ID3, TIT2, TPE1, TALB

MODES={
 'nightcore':('⚡','Nightcore','Энергичная версия: ускорение и аккуратный pitch-up без грязного клиппинга.'),
 'bass':('◉','Bass Boost','Плотный саб и низкая середина с контролем пиков, чтобы бас не превращался в перегруз.'),
 'speed':('⏩','Speed Up','Ускоренная версия с сохранением естественного тона — без чрезмерного искажения.'),
 'slow':('◀','Slow + Reverb','Замедленная атмосфера с мягким пространственным хвостом и контролем громкости.'),
 'lofi':('◒','Lo-Fi','Тёплая lo-fi обработка: мягкий roll-off, лёгкий vinyl-подобный характер и деликатная сатурация.'),
 'reverb':('◌','Reverb','Пространственная версия с коротким музыкальным хвостом и чистым центром микса.'),
 '8d':('◈','8D','Плавное стерео-движение вокруг слушателя без экстремального панорамирования.'),
 'vocal':('◇','Vocal Focus','Более выраженная середина и вокальный диапазон с мягким контролем низов и верхов.')
}

def run(cmd):
    if cmd and cmd[0]=='ffmpeg':
        cmd=[imageio_ffmpeg.get_ffmpeg_exe(), *cmd[1:]]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)

async def render(src:Path,out:Path,mode:str,cover:Path|None=None,meta:dict|None=None):
    if mode=='nightcore':
        af='atempo=1.20,asetrate=44100*1.06,aresample=44100,alimiter=limit=0.96'
    elif mode=='speed':
        af='atempo=1.12,alimiter=limit=0.96'
    elif mode=='slow':
        af='atempo=0.88,aecho=0.8:0.7:90:0.22,alimiter=limit=0.96'
    elif mode=='bass':
        af='bass=g=8:f=90:w=0.7,equalizer=f=160:g=3:w=1,alimiter=limit=0.93'
    elif mode=='lofi':
        af='lowpass=f=5200,highpass=f=120,aecho=0.8:0.55:35:0.10,alimiter=limit=0.94'
    elif mode=='reverb':
        af='aecho=0.8:0.7:80|160:0.22|0.12,alimiter=limit=0.95'
    elif mode=='8d':
        af='apulsator=mode=sine:hz=0.10:width=0.8,alimiter=limit=0.95'
    elif mode=='vocal':
        af='highpass=f=110,equalizer=f=1800:g=3:w=1.0,lowpass=f=12000,alimiter=limit=0.95'
    else:
        af='alimiter=limit=0.96'
    cmd=['ffmpeg','-y','-i',str(src),'-vn','-af',af,'-c:a','libmp3lame','-b:a','256k','-ar','44100','-ac','2',str(out)]
    await asyncio.to_thread(run,cmd)

def tag(path,meta):
    try: tags=ID3(path)
    except: tags=ID3()
    if meta.get('title'): tags['TIT2']=TIT2(encoding=3,text=meta['title'])
    if meta.get('artist'): tags['TPE1']=TPE1(encoding=3,text=meta['artist'])
    if meta.get('album'): tags['TALB']=TALB(encoding=3,text=meta['album'])
    tags.save(path,v2_version=3)

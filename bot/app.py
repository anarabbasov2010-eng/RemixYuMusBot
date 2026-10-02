import asyncio, os, shutil, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from .config import BOT_TOKEN, ADMIN_ID, FREE_DAILY, REF_BONUS, TMP_DIR
from .db import *
from .audio import MODES, render

bot=Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp=Dispatcher()
pending={}

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type','text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'RemixYuMusBot OK')
    def log_message(self,*args): pass

def start_health():
    port=int(os.getenv('PORT','10000'))
    HTTPServer(('0.0.0.0',port),HealthHandler).serve_forever()

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text='✦ Ремикс',callback_data='remix'),InlineKeyboardButton(text='◉ Профиль',callback_data='profile')],
      [InlineKeyboardButton(text='▣ Обложка и метаданные',callback_data='meta'),InlineKeyboardButton(text='↗ Пригласить',callback_data='ref')],
      [InlineKeyboardButton(text='ℹ Как это работает',callback_data='help')]
    ])

def modes_kb():
    rows=[]
    for k,(ico,name,_) in MODES.items():
        rows.append([InlineKeyboardButton(text=f'{ico} {name}',callback_data='mode:'+k)])
    rows.append([InlineKeyboardButton(text='← Назад',callback_data='home')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def is_admin(uid): return uid==ADMIN_ID

def intro(name):
    return (f'◼ <b>RemixYuMus</b>\n\nПривет, {name}. Отправь песню — я подготовлю чистую версию в выбранном стиле.\n\n'
    'Каждый режим обрабатывается отдельной цепочкой: скорость/тон, динамика, пространственная обработка и финальный limiter. Цель — сохранить громкость и избежать цифрового клиппинга.\n\n'
    '🎧 <b>Бесплатно:</b> 3 ремикса в сутки. Лимит обновляется ежедневно.\n✦ <b>Баланс:</b> дополнительные ремиксы за рефералов.')

@dp.message(CommandStart())
async def start(m:Message):
    ref=None
    if m.text and len(m.text.split())>1:
        try: ref=int(m.text.split()[1])
        except: pass
        if ref==m.from_user.id: ref=None
    ensure_user(m.from_user.id,m.from_user.username,m.from_user.first_name,ref)
    await m.answer(intro(m.from_user.first_name or 'друг'),reply_markup=menu())

@dp.callback_query(F.data=='home')
async def home(c:CallbackQuery):
    await c.message.edit_text(intro(c.from_user.first_name or 'друг'),reply_markup=menu())
    await c.answer()

@dp.callback_query(F.data=='remix')
async def remix(c:CallbackQuery):
    await c.message.edit_text('✦ <b>Выбери стиль</b>\n\nУ каждого режима своя аккуратная цепочка обработки. Нажми вариант — затем отправь аудио.',reply_markup=modes_kb())
    await c.answer()

@dp.callback_query(F.data.startswith('mode:'))
async def mode(c:CallbackQuery):
    k=c.data.split(':',1)[1]
    if k not in MODES:
        await c.answer('Неизвестный режим',show_alert=True); return
    pending[c.from_user.id]={'mode':k}
    ico,name,desc=MODES[k]
    await c.message.edit_text(f'{ico} <b>{name}</b>\n\n{desc}\n\n🎵 Теперь отправь песню как <b>Аудио</b> или <b>Документ</b>.',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='← Стили',callback_data='remix')]]))
    await c.answer()

@dp.callback_query(F.data=='profile')
async def profile(c:CallbackQuery):
    u=get_user(c.from_user.id)
    from datetime import datetime, timezone
    today=datetime.now(timezone.utc).date().isoformat()
    used=u['daily_used'] if u['daily_date']==today else 0
    free=max(0,FREE_DAILY-used)
    status='ADMIN • без лимитов' if is_admin(c.from_user.id) else ('PREMIUM' if u['premium'] else 'FREE')
    available='∞' if is_admin(c.from_user.id) or u['premium'] else str(free)
    await c.message.edit_text(f'◉ <b>Профиль</b>\n\nID: <code>{u["id"]}</code>\nСтатус: <b>{status}</b>\nБаланс: <b>{u["balance"]}</b> ремиксов\nСегодня доступно: <b>{available}</b>',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='← Назад',callback_data='home')]]))
    await c.answer()

@dp.callback_query(F.data=='ref')
async def ref(c:CallbackQuery):
    me=await bot.get_me()
    link=f'https://t.me/{me.username}?start={c.from_user.id}'
    await c.message.edit_text(f'↗ <b>Реферальная программа</b>\n\nПригласи друга по ссылке:\n<code>{link}</code>\n\nПосле того как приглашённый пользователь сделает свой первый ремикс, <b>вы оба получите +{REF_BONUS}</b> ремикса.',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='← Назад',callback_data='home')]]))
    await c.answer()

@dp.callback_query(F.data=='help')
async def help_(c:CallbackQuery):
    await c.message.edit_text('ℹ <b>Как это работает</b>\n\n1. Выбери режим.\n2. Отправь аудио.\n3. Бот скачает оригинал во временное хранилище.\n4. FFmpeg применит конкретную DSP-цепочку.\n5. Лимитер контролирует пики.\n6. Готовый файл возвращается тебе и временные файлы удаляются.\n\nОбложку и теги можно менять отдельно.',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='← Назад',callback_data='home')]]))
    await c.answer()

@dp.callback_query(F.data=='meta')
async def meta(c:CallbackQuery):
    pending[c.from_user.id]={'meta_mode':'await_audio'}
    await c.message.edit_text('▣ <b>Обложка и метаданные</b>\n\nШаг 1/3 — отправь песню. Затем я попрошу новое изображение и данные: название, автора и альбом. Исходный звук не изменяется.')
    await c.answer()

async def process(m:Message, file_id:str, name:str):
    state=pending.get(m.from_user.id,{})
    if state.get('meta_mode')=='await_audio':
        work=TMP_DIR/str(m.from_user.id); work.mkdir(parents=True,exist_ok=True)
        srcp=work/'meta_source'
        await bot.download(file_id,destination=srcp)
        pending[m.from_user.id]={'meta_mode':'await_cover','source':str(srcp),'name':name}
        await m.answer('▣ <b>Шаг 2/3 — обложка</b>\n\nОтправь новое фото обложки. Лучше квадрат 1000×1000+ px. Оригинальный звук останется без изменений.')
        return
    uid=m.from_user.id
    ok,_,_=consume(uid)
    if not ok and not is_admin(uid):
        await m.answer('◼ Лимит на сегодня исчерпан. Пригласи друга или используй накопленный баланс ремиксов.')
        return
    state=pending.pop(uid,{})
    mode=state.get('mode','nightcore')
    work=TMP_DIR/str(uid); work.mkdir(parents=True,exist_ok=True)
    srcp=work/'source'; out=work/f'{Path(name).stem}_{mode}.mp3'
    try:
        await bot.download(file_id,destination=srcp)
        await m.answer(f'◌ <b>Обрабатываю: {MODES[mode][1]}</b>\n\nЦепочка: подготовка → DSP → контроль пиков → экспорт 256 kbps.\nПожалуйста, подожди.')
        await render(srcp,out,mode)
        await m.answer_audio(FSInputFile(out),caption=f'{MODES[mode][0]} {MODES[mode][1]}\n{MODES[mode][2]}')
        ref=mark_referral(uid)
        if ref:
            add_balance(uid,REF_BONUS); add_balance(ref,REF_BONUS)
            await bot.send_message(ref,f'↗ Реферальный бонус активирован: +{REF_BONUS} ремикса.')
            await m.answer(f'✦ Реферальный бонус активирован: тебе +{REF_BONUS} ремикса.')
    except Exception as e:
        await m.answer('⚠️ Не удалось обработать файл. Попробуй MP3/M4A/WAV/OGG или другой файл.')
        print('PROCESS ERROR',repr(e))
    finally:
        shutil.rmtree(work,ignore_errors=True)

@dp.message(F.photo)
async def cover_photo(m:Message):
    state=pending.get(m.from_user.id,{})
    if state.get('meta_mode')!='await_cover': return
    work=TMP_DIR/str(m.from_user.id); cover=work/'cover.jpg'
    work.mkdir(parents=True,exist_ok=True)
    await bot.download(m.photo[-1].file_id,destination=cover)
    state['meta_mode']='await_tags'; state['cover']=str(cover); pending[m.from_user.id]=state
    await m.answer('▣ <b>Шаг 3/3 — данные</b>\n\nОтправь одной строкой в формате:\n<code>Название | Автор | Альбом</code>\n\nНапример: <code>After Dark | Mr.Kitty | Time</code>')

@dp.message(F.text)
async def metadata_text(m:Message):
    state=pending.get(m.from_user.id,{})
    if state.get('meta_mode')!='await_tags': return
    parts=[x.strip() for x in m.text.split('|')]
    if len(parts)<2:
        await m.answer('Формат нужен такой: <code>Название | Автор | Альбом</code>'); return
    title,artist=parts[0],parts[1]; album=parts[2] if len(parts)>2 else ''
    work=TMP_DIR/str(m.from_user.id); out=work/'edited.mp3'
    try:
        import subprocess, imageio_ffmpeg
        cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',state['source'],'-i',state['cover'],'-map','0:a:0','-map','1:v:0','-c:a','copy','-c:v','mjpeg','-disposition:v:0','attached_pic','-id3v2_version','3','-metadata',f'title={title}','-metadata',f'artist={artist}']
        if album: cmd += ['-metadata',f'album={album}']
        cmd += [str(out)]
        await asyncio.to_thread(subprocess.run,cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        await m.answer_audio(FSInputFile(out),caption=f'✓ <b>Готово</b>\n{title} — {artist}'+(f'\n{album}' if album else ''))
    except Exception as e:
        print('META ERROR',repr(e)); await m.answer('⚠️ Не удалось изменить метаданные. Попробуй JPG/PNG и аудиофайл MP3/M4A.')
    finally:
        pending.pop(m.from_user.id,None); shutil.rmtree(work,ignore_errors=True)

@dp.message(F.audio)
async def audio(m:Message):
    await process(m,m.audio.file_id,m.audio.file_name or 'track.mp3')

@dp.message(F.document)
async def document(m:Message):
    name=m.document.file_name or 'track'
    if m.document.mime_type and (m.document.mime_type.startswith('audio/') or name.lower().endswith(('.mp3','.m4a','.wav','.ogg','.flac'))):
        await process(m,m.document.file_id,name)

@dp.message(Command('admin'))
async def admin(m:Message):
    if not is_admin(m.from_user.id): return
    s=stats()
    await m.answer(f'◈ <b>ADMIN</b>\nПользователи: {s["users"]}\nPremium: {s["premium"]}\nБаланс выданных ремиксов: {s["balance"]}\n\nКоманды: /premium ID, /give ID COUNT')

@dp.message(Command('premium'))
async def premium(m:Message):
    if not is_admin(m.from_user.id): return
    p=m.text.split()
    if len(p)>=2:
        set_premium(int(p[1]),True); await m.answer('✓ Premium включён.')

@dp.message(Command('give'))
async def give(m:Message):
    if not is_admin(m.from_user.id): return
    p=m.text.split()
    if len(p)>=3:
        add_balance(int(p[1]),int(p[2])); await m.answer('✓ Баланс пополнен.')

async def main():
    if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN is not set')
    init()
    threading.Thread(target=start_health,daemon=True).start()
    await dp.start_polling(bot)

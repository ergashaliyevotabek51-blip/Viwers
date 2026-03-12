from database import get_channels, save_channels
from datetime import datetime

async def check_subscription(user_id: int, context) -> bool:
    """Majburiy obunani tekshirish"""
    channels = get_channels()
    if not channels:
        return True
    
    for channel_id, info in channels.items():
        try:
            # ID bo'lsa integer ga o'tkazamiz
            if channel_id.lstrip('-').isdigit():
                ch_id = int(channel_id)
            else:
                ch_id = channel_id  # Username @channel ko'rinishida
            
            member = await context.bot.get_chat_member(ch_id, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            print(f"Kanal tekshirish xatosi {channel_id}: {e}")
            continue
    return True

def add_channel(channel_id: str, name: str, invite_link: str = ""):
    """Kanal qo'shish - ID yoki username bo'lishi mumkin"""
    channels = get_channels()
    
    # Agar username bo'lsa (@ bilan boshlansa)
    if channel_id.startswith('@'):
        clean_id = channel_id
    # Agar link bo'lsa (https://t.me/...)
    elif channel_id.startswith('https://t.me/'):
        clean_id = '@' + channel_id.split('/')[-1]
    # Agar ID bo'lsa (-100...)
    elif channel_id.startswith('-100'):
        clean_id = channel_id
    else:
        clean_id = channel_id
    
    channels[clean_id] = {
        "name": name,
        "invite_link": invite_link,
        "added_at": datetime.now().isoformat()
    }
    save_channels(channels)

def remove_channel(channel_id: str) -> bool:
    """Kanal o'chirish"""
    channels = get_channels()
    if channel_id in channels:
        del channels[channel_id]
        save_channels(channels)
        return True
    return False

from database import get_channels

async def check_subscription(user_id: int, context) -> bool:
    channels = get_channels()
    if not channels:
        return True
    
    for channel_id in channels:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            continue
    return True

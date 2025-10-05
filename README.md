# filerename
# Advanced File Renamer Bot

## Deployment to Vercel

1. **Fork this repository** or create a new one with these files

2. **Set environment variables in Vercel:**
   - `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather

3. **Deploy to Vercel:**
   - Connect your GitHub repo to Vercel
   - Deploy automatically

4. **Set webhook:**
   - After deployment, visit: `https://your-app.vercel.app/set_webhook`
   - You should see "Webhook set" message

## Features

- ✅ Multiple file type support
- ✅ Custom prefix/suffix settings
- ✅ Custom renaming with /rename command
- ✅ File size validation
- ✅ User preferences
- ✅ Inline keyboard interface
- ✅ Error handling and logging

## Local Development

```bash
pip install -r requirements.txt
python bot.py
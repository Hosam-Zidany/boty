import os
import zipfile
import tempfile
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Get the token
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TEMP_DIR = tempfile.mkdtemp(prefix="video_bot_")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send instructions when the command /start is issued."""
    await update.message.reply_text(
        "📹 Video Collector Bot\n\n"
        "1. Send me video files with descriptions (captions)\n"
        "2. I'll collect them all\n"
        "3. Send /zip when you're done to get a zip file\n"
        "4. All videos will be named according to their descriptions\n\n"
        "Send your first video with a description to begin!"
    )
    # Initialize user data
    context.user_data['videos'] = []

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming video files with descriptions."""
    # Check if user data is initialized
    if 'videos' not in context.user_data:
        context.user_data['videos'] = []

    # Get the video file
    video_file = update.message.video or update.message.document
    if not video_file:
        await update.message.reply_text("⚠️ Please send a valid video file!")
        return

    # Get the description (caption)
    description = update.message.caption
    if not description:
        await update.message.reply_text("⚠️ Please include a description (caption) with your video!")
        return

    # Sanitize the description to create a valid filename
    sanitized_name = "".join(
        c for c in description if c.isalnum() or c in (' ', '-', '_')
    ).strip().replace(' ', '_') + '.mp4'

    # Download the video
    file = await context.bot.get_file(video_file.file_id)
    temp_video_path = os.path.join(TEMP_DIR, f"temp_{update.effective_user.id}_{video_file.file_unique_id}.mp4")
    await file.download_to_drive(temp_video_path)

    # Store the video with its new name
    context.user_data['videos'].append({
        'path': temp_video_path,
        'name': sanitized_name
    })

    await update.message.reply_text(
        f"✅ Video saved as: {sanitized_name}\n"
        f"Total videos collected: {len(context.user_data['videos'])}\n"
        "Send more videos or /zip when done"
    )

async def create_zip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create and send a zip file of all collected videos."""
    if 'videos' not in context.user_data or not context.user_data['videos']:
        await update.message.reply_text("⚠️ No videos collected yet!")
        return

    # Use the first video's sanitized name (without extension) as ZIP filename
    base_name = os.path.splitext(context.user_data['videos'][0]['name'])[0]
    zip_filename = f"{base_name}.zip"
    zip_path = os.path.join(TEMP_DIR, f"videos_{update.effective_user.id}.zip")

    try:
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for video in context.user_data['videos']:
                zipf.write(video['path'], video['name'])

        # Send the zip file with the custom name
        await update.message.reply_document(
            document=open(zip_path, 'rb'),
            caption="Here are your videos with descriptive names!",
            filename=zip_filename  # Using the custom filename here
        )

        cleanup_files(context.user_data['videos'], zip_path)
        context.user_data['videos'] = []

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error creating zip file: {str(e)}")
        cleanup_files(context.user_data['videos'], zip_path)
        context.user_data['videos'] = []

def cleanup_files(videos: list, zip_path: str) -> None:
    """Clean up all temporary files."""
    for video in videos:
        try:
            if os.path.exists(video['path']):
                os.remove(video['path'])
        except:
            pass

    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
    except:
        pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and clean up if needed."""
    print(f"Error while processing update: {context.error}")
    if update and update.effective_user:
        if 'videos' in context.user_data:
            zip_path = os.path.join(TEMP_DIR, f"videos_{update.effective_user.id}.zip")
            cleanup_files(context.user_data['videos'], zip_path)
            context.user_data['videos'] = []

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("zip", create_zip))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    application.add_error_handler(error_handler)

    # Run the bot
    application.run_polling()

    # Clean up on exit
    for filename in os.listdir(TEMP_DIR):
        try:
            os.remove(os.path.join(TEMP_DIR, filename))
        except:
            pass

if __name__ == '__main__':
    main()import os

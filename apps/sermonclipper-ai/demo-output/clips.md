# SermonClipper AI Suggestions

Source: demo-sermon

These clips are ranked by sermon-highlight language, emotional/practical punch, and Shorts-friendly duration.

## 1. Promise Grace Faith Mercy Lord

- **Time:** 00:38–01:18
- **Duration:** 40 seconds
- **Score:** 51.0
- **Why this clip:** Keywords: alone, faith, god, grace, lord, mercy, pray, promise; duration 40s
- **Description:** A sermon highlight about alone, faith, god, grace: But don't miss this promise: grace meets you in the middle of your failure. When you feel alone, the Lord is near, and mercy is new every morning. So respond with faith this...
- **Hashtags:** #sermonclip #faith #church #prayer #grace
- **Suggested filename:** `01-promise-grace-faith-mercy-lord.mp4`

### Transcript excerpt

> But don't miss this promise: grace meets you in the middle of your failure. When you feel alone, the Lord is near, and mercy is new every morning. So respond with faith this week and take one step of obedience. Let us pray and ask God to make this truth real in our hearts.

### Render command template

```bash
yt-dlp -f 'bv*+ba/b' -o source.%(ext)s 'demo-sermon'
sermonclipper render source.mp4 --start 38 --end 78 --output 01-promise-grace-faith-mercy-lord.mp4 --vertical --captions "Promise Grace Faith Mercy Lord"
```

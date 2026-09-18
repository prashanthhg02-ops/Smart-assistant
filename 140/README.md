# Smart AIML Assistant

Nova is a small browser-based assistant powered by AIML categories. It uses only the Python standard library, so there are no dependencies to install.

## Run

```powershell
python app.py
```

Then open http://127.0.0.1:8000. The server opens the page automatically in most desktop environments.

## Teach Nova

Add a category to `aiml/brain.aiml`:

```xml
<category>
  <pattern>YOUR QUESTION</pattern>
  <template>Your answer.</template>
</category>
```

Patterns are case-insensitive. Use `*` to capture a phrase, for example `CALCULATE *`. The built-in dynamic tokens are `{TIME}`, `{DATE}`, and `{CALC}`.

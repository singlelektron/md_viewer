//! Document rendering and the editor protocol, independent of the desktop runtime.

use pulldown_cmark::{Event, Options, Parser, html};
use serde::{Deserialize, Serialize};
use std::io::BufRead;

pub const MAX_FRAME_BYTES: usize = 2 * 1024 * 1024;
pub const MAX_DOCUMENT_BYTES: usize = 1024 * 1024;
pub const THEMES: [&str; 3] = ["moonlit", "graphite", "paper"];

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Update {
    pub version: u8,
    #[serde(rename = "type")]
    pub kind: String,
    pub revision: u64,
    pub name: String,
    pub text: String,
    pub modified: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct Preview {
    pub revision: u64,
    pub title: String,
    pub html: String,
    pub modified: bool,
    pub theme: String,
    pub connected: bool,
    pub error: Option<String>,
}

impl Default for Preview {
    fn default() -> Self {
        Self {
            revision: 0,
            title: "md_viewer".into(),
            html: String::new(),
            modified: false,
            theme: "moonlit".into(),
            connected: false,
            error: None,
        }
    }
}

impl Preview {
    /// Returns false for an obsolete snapshot, without disturbing newer content.
    pub fn apply(&mut self, update: Update) -> Result<bool, String> {
        if update.version != 1 || update.kind != "update" {
            return Err("Unsupported editor protocol; expected version 1 update.".into());
        }
        if update.revision > 9_007_199_254_740_991 {
            return Err("Editor revision exceeds the safe integer range.".into());
        }
        if update.text.len() > MAX_DOCUMENT_BYTES || update.name.len() > 4096 {
            return Err("Note exceeds the 1 MiB preview limit, or its name is too long.".into());
        }
        if update.revision <= self.revision {
            return Ok(false);
        }
        self.html = render_markdown(&update.text);
        self.revision = update.revision;
        // Only a filename is displayed. Full source paths are never sent to the view.
        self.title = update
            .name
            .rsplit(['/', '\\'])
            .next()
            .unwrap_or("[No Name]")
            .to_owned();
        if self.title.is_empty() {
            self.title = "[No Name]".into();
        }
        self.modified = update.modified;
        self.connected = true;
        self.error = None;
        Ok(true)
    }

    pub fn set_theme(&mut self, theme: &str) -> Result<(), String> {
        if !THEMES.contains(&theme) {
            return Err("Unknown theme. Choose moonlit, graphite, or paper.".into());
        }
        self.theme = theme.into();
        Ok(())
    }
}

fn escape_html(source: &str) -> String {
    source
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#39;")
}

pub fn render_markdown(source: &str) -> String {
    let options = Options::ENABLE_MATH
        | Options::ENABLE_TABLES
        | Options::ENABLE_STRIKETHROUGH
        | Options::ENABLE_TASKLISTS;
    let events = Parser::new_ext(source, options).map(|event| match event {
        Event::InlineMath(tex) => Event::Html(
            format!(
                "<span class=\"math-inline\" data-tex=\"{}\">{}</span>",
                escape_html(&tex),
                escape_html(&tex)
            )
            .into(),
        ),
        Event::DisplayMath(tex) => Event::Html(
            format!(
                "<div class=\"math-display\" data-tex=\"{}\">{}</div>",
                escape_html(&tex),
                escape_html(&tex)
            )
            .into(),
        ),
        Event::Html(text) | Event::InlineHtml(text) => Event::Text(text),
        other => other,
    });
    let mut rendered = String::new();
    html::push_html(&mut rendered, events);
    // No remote or local images are loaded; raw HTML is text, links remain inert
    // in the view, and a strict CSP is a second boundary around document content.
    ammonia::Builder::default()
        .rm_tags(&["img"])
        // DOM click handlers alone do not cover a native WebView's link menu.
        .rm_tag_attributes("a", &["href"])
        .add_tag_attributes("span", &["class", "data-tex"])
        .add_tag_attributes("div", &["class", "data-tex"])
        .add_tag_attributes("code", &["class"])
        .clean(&rendered)
        .to_string()
}

/// Read one bounded NDJSON frame without allocating an unbounded input line.
pub fn read_update(reader: &mut impl BufRead) -> Result<Option<Update>, String> {
    use std::io::Read;
    let mut line = Vec::new();
    let size = reader
        .take((MAX_FRAME_BYTES + 1) as u64)
        .read_until(b'\n', &mut line)
        .map_err(|err| err.to_string())?;
    if size == 0 {
        return Ok(None);
    }
    if size > MAX_FRAME_BYTES {
        return Err("Editor message exceeds the 2 MiB transport limit.".into());
    }
    serde_json::from_slice(&line)
        .map(Some)
        .map_err(|err| format!("Invalid editor update: {err}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    fn update(revision: u64, text: &str) -> Update {
        Update {
            version: 1,
            kind: "update".into(),
            revision,
            name: "/notes/数学.md".into(),
            text: text.into(),
            modified: true,
        }
    }

    #[test]
    fn math_is_parsed_without_interpreting_code_or_escaped_dollars() {
        let html =
            render_markdown("公式 $x^2 + \\frac{1}{2}$; `code $x$` and \\$5.\n\n```\n$x$\n```\n");
        assert_eq!(html.matches("data-tex=").count(), 1);
        assert!(html.contains("\\frac{1}{2}"));
        assert!(html.contains("<code>code $x$</code>"));
        assert!(html.contains("公式"));
    }

    #[test]
    fn raw_html_links_images_and_math_attributes_cannot_inject_active_content() {
        let html = render_markdown(
            "<script>alert(1)</script>\n\n[x](javascript:alert%281%29) ![pic](https://example.com/a.png)\n\n$x\" onmouseover=\"alert(1)$",
        );
        assert!(!html.contains("<script>"));
        assert!(!html.contains("href=\"javascript:"));
        assert!(!html.contains("<img"));
        let math_tag = html
            .split("<span")
            .nth(1)
            .unwrap()
            .split('>')
            .next()
            .unwrap();
        assert!(!math_tag.contains(" onmouseover=\""));
        assert!(html.contains("&quot;"));
    }

    #[test]
    fn incomplete_math_keeps_document_and_recovers_on_next_snapshot() {
        let mut preview = Preview::default();
        preview
            .apply(update(1, "before $\\frac{1}{$ after"))
            .unwrap();
        assert!(preview.html.contains("before"));
        preview.apply(update(2, "after $\\frac{1}{2}$")).unwrap();
        assert_eq!(preview.revision, 2);
        assert_eq!(preview.title, "数学.md");
        assert!(preview.modified);
        assert!(preview.html.contains("data-tex="));
    }

    #[test]
    fn links_have_no_navigation_target_including_native_context_menus() {
        let html = render_markdown(
            "[web](https://example.com) [local](other.md) [file](file:///tmp/a) [anchor](#section)",
        );
        assert!(html.contains("web</a>"));
        assert!(!html.contains("href="));
    }

    #[test]
    fn stale_updates_and_invalid_inputs_preserve_the_current_document() {
        let mut preview = Preview::default();
        preview.apply(update(4, "new")).unwrap();
        assert!(!preview.apply(update(3, "old")).unwrap());
        assert!(preview.html.contains("new"));
        assert!(preview.set_theme("other").is_err());
        assert_eq!(preview.theme, "moonlit");
        assert!(
            preview
                .apply(update(5, &"x".repeat(MAX_DOCUMENT_BYTES + 1)))
                .is_err()
        );
        assert_eq!(preview.revision, 4);
    }

    #[test]
    fn protocol_handles_multiple_frames_unicode_eof_and_size_limits() {
        let input = concat!(
            "{\"version\":1,\"type\":\"update\",\"revision\":1,\"name\":\"数学.md\",\"text\":\"α\\n$x$\",\"modified\":true}\n",
            "{\"version\":1,\"type\":\"update\",\"revision\":2,\"name\":\"b.md\",\"text\":\"b\",\"modified\":false}\n"
        );
        let mut reader = Cursor::new(input);
        assert_eq!(read_update(&mut reader).unwrap().unwrap().text, "α\n$x$");
        assert_eq!(read_update(&mut reader).unwrap().unwrap().revision, 2);
        assert!(read_update(&mut reader).unwrap().is_none());
        assert!(read_update(&mut Cursor::new(vec![b'x'; MAX_FRAME_BYTES + 1])).is_err());
        assert!(read_update(&mut Cursor::new(b"not json\n")).is_err());
    }
}

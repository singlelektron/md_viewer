use md_viewer::{MAX_DOCUMENT_BYTES, Preview, Update, read_update};
use std::{
    env,
    fs::File,
    io::{self, BufReader, Read},
    path::PathBuf,
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};
use tauri::{Emitter, Manager, State};

#[derive(Clone)]
struct Shared(Arc<Mutex<Preview>>);

#[cfg(target_os = "macos")]
fn native_theme(theme: &str) -> tauri::Theme {
    if theme == "paper" {
        tauri::Theme::Light
    } else {
        tauri::Theme::Dark
    }
}

#[tauri::command]
fn get_preview(state: State<'_, Shared>) -> Preview {
    state.0.lock().expect("preview lock").clone()
}

#[tauri::command]
fn set_theme(
    theme: String,
    state: State<'_, Shared>,
    app: tauri::AppHandle,
) -> Result<Preview, String> {
    let mut preview = state.0.lock().map_err(|_| "Preview state unavailable")?;
    preview.set_theme(&theme)?;
    #[cfg(target_os = "macos")]
    if let Some(window) = app.get_webview_window("main") {
        window
            .set_theme(Some(native_theme(&theme)))
            .map_err(|err| err.to_string())?;
    }
    // Serialize emissions with edits so equal-revision theme events cannot race.
    app.emit("preview-updated", &*preview)
        .map_err(|err| err.to_string())?;
    Ok(preview.clone())
}

#[tauri::command]
fn frontend_ready() {
    // Ready means the listener is installed; content may still arrive afterwards.
}

enum Input {
    Empty,
    Stdin,
    File(PathBuf),
}

fn arguments() -> Result<(Input, String), String> {
    let mut mode = Input::Empty;
    let mut theme = "moonlit".to_owned();
    let mut arguments = env::args().skip(1);
    while let Some(arg) = arguments.next() {
        match arg.as_str() {
            "--help" | "-h" => {
                println!(
                    "md-viewer [FILE | --stdin] [--theme moonlit|graphite|paper]\n\
                    FILE: preview a UTF-8 Markdown file and refresh saved changes.\n\
                    --stdin: receive unsaved Neovim snapshots through the bundled Lua integration.\n\
                    With no input, open the connection instructions. Notes are never modified."
                );
                std::process::exit(0);
            }
            "--version" | "-V" => {
                println!("md-viewer {}", env!("CARGO_PKG_VERSION"));
                std::process::exit(0);
            }
            "--theme" => theme = arguments.next().ok_or("Missing theme name")?,
            "--stdin" if matches!(mode, Input::Empty) => mode = Input::Stdin,
            "--" if matches!(mode, Input::Empty) => {
                mode = Input::File(arguments.next().ok_or("Missing file after --")?.into());
                if arguments.next().is_some() {
                    return Err("Only one note can be opened.".into());
                }
            }
            _ if !arg.starts_with('-') && matches!(mode, Input::Empty) => {
                mode = Input::File(arg.into())
            }
            _ => return Err(format!("Unexpected argument: {arg}. Use --help for usage.")),
        }
    }
    if !md_viewer::THEMES.contains(&theme.as_str()) {
        return Err("Unknown theme. Choose moonlit, graphite, or paper.".into());
    }
    Ok((mode, theme))
}

fn publish(app: &tauri::AppHandle, shared: &Shared, update: Update) {
    let mut preview = shared.0.lock().expect("preview lock");
    match preview.apply(update) {
        Ok(false) => return,
        Ok(true) => (),
        Err(err) => preview.error = Some(err),
    }
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.set_title(&format!("{} — md_viewer", preview.title));
    }
    let _ = app.emit("preview-updated", &*preview);
}

fn report_error(app: &tauri::AppHandle, shared: &Shared, message: String) {
    let mut preview = shared.0.lock().expect("preview lock");
    if preview.error.as_deref() == Some(&message) {
        return;
    }
    preview.error = Some(message);
    preview.connected = false;
    let _ = app.emit("preview-updated", &*preview);
}

fn read_note(path: &PathBuf) -> Result<String, String> {
    let mut bytes = Vec::new();
    File::open(path)
        .map_err(|err| format!("Could not open note: {err}"))?
        .take((MAX_DOCUMENT_BYTES + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|err| format!("Could not read note: {err}"))?;
    if bytes.len() > MAX_DOCUMENT_BYTES {
        return Err("Note exceeds the 1 MiB preview limit.".into());
    }
    String::from_utf8(bytes).map_err(|_| "The note must be UTF-8 text.".into())
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let (mode, theme) = arguments().map_err(io::Error::other)?;
    let mut preview = Preview::default();
    preview.set_theme(&theme)?;
    let shared = Shared(Arc::new(Mutex::new(preview)));
    tauri::Builder::default()
        .manage(shared.clone())
        .invoke_handler(tauri::generate_handler![
            get_preview,
            set_theme,
            frontend_ready
        ])
        .setup(move |app| {
            #[cfg(target_os = "macos")]
            if let Some(window) = app.get_webview_window("main") {
                window.set_theme(Some(native_theme(&theme)))?;
            }
            let handle = app.handle().clone();
            // Document navigation targets are removed by the Rust sanitizer.
            match mode {
                Input::Empty => (),
                Input::Stdin => {
                    thread::spawn(move || {
                        let mut input = BufReader::new(io::stdin());
                        loop {
                            match read_update(&mut input) {
                                Ok(Some(update)) => publish(&handle, &shared, update),
                                Ok(None) => {
                                    handle.exit(0);
                                    break;
                                }
                                Err(error) => {
                                    report_error(&handle, &shared, error);
                                    break;
                                }
                            }
                        }
                    });
                }
                Input::File(path) => {
                    thread::spawn(move || {
                        let mut previous = None;
                        let mut revision = 0;
                        loop {
                            match read_note(&path) {
                                Ok(text) => {
                                    let recovering =
                                        shared.0.lock().expect("preview lock").error.is_some();
                                    if previous.as_ref() != Some(&text) || recovering {
                                        revision += 1;
                                        publish(
                                            &handle,
                                            &shared,
                                            Update {
                                                version: 1,
                                                kind: "update".into(),
                                                revision,
                                                name: path.to_string_lossy().into_owned(),
                                                text: text.clone(),
                                                modified: false,
                                            },
                                        );
                                        previous = Some(text);
                                    }
                                }
                                Err(error) => report_error(&handle, &shared, error),
                            }
                            // Full, bounded reads also observe atomic replacement and equal-length edits.
                            thread::sleep(Duration::from_millis(350));
                        }
                    });
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())?;
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("md-viewer: {error}");
        std::process::exit(1);
    }
}

use crate::{compress, gs};
use anyhow::{anyhow, Result};
use eframe::egui;
use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver, TryRecvError};

type WorkerResult = Result<(compress::CompressionResult, PathBuf), String>;
enum WorkerMessage {
    Progress(compress::CompressionStage),
    Finished(WorkerResult),
}

pub fn run() -> Result<()> {
    let icon = eframe::icon_data::from_png_bytes(include_bytes!(
        "../assets/icons/hicolor/256x256/apps/pdf-squeeze.png"
    ))?;
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_icon(icon),
        ..Default::default()
    };
    eframe::run_native(
        "PDF Squeeze",
        options,
        Box::new(|cc| Ok(Box::new(PdfSqueezeApp::new(cc)))),
    )
    .map_err(|error| anyhow!("{error}"))
}

struct PdfSqueezeApp {
    dark_mode: bool,
    input: Option<PathBuf>,
    output: String,
    stage: compress::CompressionStage,
    ghostscript_error: Option<String>,
    worker: Option<Receiver<WorkerMessage>>,
    pending_result: Option<WorkerResult>,
    status: Status,
}

enum Status {
    Ready,
    Running,
    Success(compress::CompressionResult, PathBuf),
    Failure(String),
}

impl PdfSqueezeApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let app = Self {
            dark_mode: false,
            input: None,
            output: String::new(),
            stage: compress::CompressionStage::CheckingGhostscript,
            ghostscript_error: gs::check_installed().err().map(|error| error.to_string()),
            worker: None,
            pending_result: None,
            status: Status::Ready,
        };
        cc.egui_ctx.set_theme(if app.dark_mode {
            egui::ThemePreference::Dark
        } else {
            egui::ThemePreference::Light
        });
        app
    }

    fn start_compression(&mut self) {
        let Some(input) = self.input.clone() else {
            self.status = Status::Failure("Choose an input PDF first.".into());
            return;
        };
        if self.output.trim().is_empty() {
            self.status = Status::Failure("Choose an output path first.".into());
            return;
        }
        let output = PathBuf::from(&self.output);
        let (sender, receiver) = mpsc::channel();
        self.stage = compress::CompressionStage::CheckingGhostscript;
        match std::thread::Builder::new()
            .name("pdf-squeeze-compression".into())
            .spawn(move || {
                let result = compress::compress_pdf(&input, &output, |update| {
                    let _ = sender.send(WorkerMessage::Progress(update));
                })
                .map(|summary| (summary, output))
                .map_err(|error| format!("{error:#}"));
                let _ = sender.send(WorkerMessage::Finished(result));
            }) {
            Ok(_) => {
                self.worker = Some(receiver);
                self.status = Status::Running;
            }
            Err(error) => {
                self.status = Status::Failure(format!(
                    "Could not start compression: {error}. Please try again."
                ));
            }
        }
    }

    fn poll_worker(&mut self) {
        if let Some(result) = self.pending_result.take() {
            self.status = match result {
                Ok((summary, output)) => Status::Success(summary, output),
                Err(error) => Status::Failure(error),
            };
            return;
        }

        loop {
            let message = self.worker.as_ref().map(Receiver::try_recv);
            match message {
                Some(Ok(WorkerMessage::Progress(update))) => {
                    self.stage = update;
                }
                Some(Ok(WorkerMessage::Finished(result))) => {
                    self.pending_result = Some(result);
                    self.worker = None;
                    break;
                }
                Some(Err(TryRecvError::Disconnected)) => {
                    self.pending_result = Some(Err(
                        "Compression stopped unexpectedly. Please try again.".into(),
                    ));
                    self.worker = None;
                    break;
                }
                _ => break,
            }
        }
    }
}

impl eframe::App for PdfSqueezeApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll_worker();
        egui::TopBottomPanel::top("theme_controls").show(ctx, |ui| {
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                let label = if self.dark_mode {
                    "☀️ Light"
                } else {
                    "🌙 Dark"
                };
                if ui.button(label).clicked() {
                    self.dark_mode = !self.dark_mode;
                    ctx.set_theme(if self.dark_mode {
                        egui::ThemePreference::Dark
                    } else {
                        egui::ThemePreference::Light
                    });
                }
            });
        });
        egui::CentralPanel::default().show(ctx, |ui| {
            let idle = self.worker.is_none() && self.pending_result.is_none();
            ui.heading("PDF Squeeze");
            ui.add_space(12.0);

            if let Some(error) = &self.ghostscript_error {
                ui.colored_label(egui::Color32::RED, error);
                ui.add_space(10.0);
            }

            ui.label("Input PDF");
            ui.horizontal(|ui| {
                let mut display = self
                    .input
                    .as_ref()
                    .map(|path| path.to_string_lossy().into_owned())
                    .unwrap_or_default();
                ui.add_sized(
                    [(ui.available_width() - 90.0).max(80.0), 24.0],
                    egui::TextEdit::singleline(&mut display).interactive(false),
                );
                if ui.add_enabled(idle, egui::Button::new("Browse")).clicked() {
                    if let Some(path) = rfd::FileDialog::new()
                        .add_filter("PDF", &["pdf"])
                        .pick_file()
                    {
                        self.output = compress::default_output_path(&path)
                            .to_string_lossy()
                            .into_owned();
                        self.input = Some(path);
                        self.status = Status::Ready;
                    }
                }
            });

            ui.add_space(8.0);
            ui.label("One-pass compression with the /ebook profile. Image quality may change.");

            ui.add_space(8.0);
            ui.label("Output path");
            ui.horizontal(|ui| {
                ui.add_sized(
                    [(ui.available_width() - 90.0).max(80.0), 24.0],
                    egui::TextEdit::singleline(&mut self.output).interactive(idle),
                );
                if ui.add_enabled(idle, egui::Button::new("Browse")).clicked() {
                    let dialog = rfd::FileDialog::new()
                        .add_filter("PDF", &["pdf"])
                        .set_file_name(
                            PathBuf::from(&self.output)
                                .file_name()
                                .and_then(|name| name.to_str())
                                .unwrap_or("output.pdf"),
                        );
                    if let Some(path) = dialog.save_file() {
                        self.output = path.to_string_lossy().into_owned();
                    }
                }
            });

            ui.add_space(16.0);
            let valid_input = self
                .input
                .as_deref()
                .is_some_and(|input| compress::validate_input(input).is_ok());
            if self.input.is_some() && !valid_input {
                ui.label("Choose an existing PDF file to continue.");
            }
            let can_compress = valid_input && self.ghostscript_error.is_none() && idle;
            if ui
                .add_enabled(can_compress, egui::Button::new("Compress"))
                .clicked()
            {
                self.start_compression();
            }

            ui.add_space(12.0);
            match &self.status {
                Status::Ready => {}
                Status::Running => {
                    ui.horizontal(|ui| {
                        ui.spinner();
                        ui.label(self.stage.label());
                    });
                    ctx.request_repaint();
                }
                Status::Success(summary, path) => {
                    ui.label(summary.summary());
                    ui.label(format!("Saved to {}", path.display()));
                }
                Status::Failure(error) => {
                    ui.colored_label(egui::Color32::RED, error);
                }
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{Duration, Instant};

    #[test]
    #[ignore = "requires Ghostscript installed"]
    fn gui_worker_uses_the_shared_single_pass_engine() {
        let directory = tempfile::tempdir().unwrap();
        let input = PathBuf::from(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/tests/fixtures/tiny.pdf"
        ));
        let original = std::fs::read(&input).unwrap();
        let output = directory.path().join("output.pdf");
        let mut app = PdfSqueezeApp {
            dark_mode: false,
            input: Some(input.clone()),
            output: output.to_string_lossy().into_owned(),
            stage: compress::CompressionStage::CheckingGhostscript,
            ghostscript_error: None,
            worker: None,
            pending_result: None,
            status: Status::Ready,
        };

        app.start_compression();
        assert!(matches!(app.status, Status::Running));
        assert!(app.worker.is_some());
        let deadline = Instant::now() + Duration::from_secs(15);
        loop {
            app.poll_worker();
            match &app.status {
                Status::Success(summary, path) => {
                    assert_eq!(path, &output);
                    assert_eq!(summary.original_size_bytes, original.len() as u64);
                    assert_eq!(summary.size_bytes, original.len() as u64);
                    assert_eq!(summary.outcome, compress::CompressionOutcome::Unchanged);
                    assert_eq!(summary.profile, gs::CompressionProfile::Ebook);
                    assert_eq!(summary.compression_invocations, 1);
                    assert_eq!(summary.saved_percent(), 0.0);
                    assert_eq!(std::fs::read(&output).unwrap(), original);
                    assert_eq!(std::fs::read(&input).unwrap(), original);
                    assert_eq!(std::fs::read_dir(directory.path()).unwrap().count(), 1);
                    break;
                }
                Status::Failure(error) => panic!("GUI worker failed: {error}"),
                _ => {
                    assert!(Instant::now() < deadline, "GUI worker did not finish");
                    std::thread::sleep(Duration::from_millis(10));
                }
            }
        }
    }
}

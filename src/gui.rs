use crate::{compress, gs};
use anyhow::{anyhow, Result};
use eframe::egui;
use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver, TryRecvError};
use std::time::Duration;

type WorkerResult = Result<(compress::SearchResult, PathBuf, f64), String>;

pub fn run() -> Result<()> {
    eframe::run_native(
        "PDF Squeeze",
        eframe::NativeOptions::default(),
        Box::new(|_| Ok(Box::new(PdfSqueezeApp::new()))),
    )
    .map_err(|error| anyhow!("{error}"))
}

struct PdfSqueezeApp {
    input: Option<PathBuf>,
    output: String,
    target_mb: f64,
    ghostscript_error: Option<String>,
    worker: Option<Receiver<WorkerResult>>,
    status: Status,
}

enum Status {
    Ready,
    Running,
    Success(compress::SearchResult, PathBuf, f64),
    Failure(String),
}

impl PdfSqueezeApp {
    fn new() -> Self {
        Self {
            input: None,
            output: String::new(),
            target_mb: 50.0,
            ghostscript_error: gs::check_installed().err().map(|error| error.to_string()),
            worker: None,
            status: Status::Ready,
        }
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
        let target_mb = self.target_mb;
        let (sender, receiver) = mpsc::channel();
        match std::thread::Builder::new()
            .name("pdf-squeeze-compression".into())
            .spawn(move || {
                let result = compress::compress_pdf(&input, &output, target_mb)
                    .map(|summary| (summary, output, target_mb))
                    .map_err(|error| format!("{error:#}"));
                let _ = sender.send(result);
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
        let result = self.worker.as_ref().map(Receiver::try_recv);
        match result {
            Some(Ok(Ok((summary, output, target_mb)))) => {
                self.status = Status::Success(summary, output, target_mb);
                self.worker = None;
            }
            Some(Ok(Err(error))) => {
                self.status = Status::Failure(error);
                self.worker = None;
            }
            Some(Err(TryRecvError::Disconnected)) => {
                self.status =
                    Status::Failure("Compression stopped unexpectedly. Please try again.".into());
                self.worker = None;
            }
            _ => {}
        }
    }
}

impl eframe::App for PdfSqueezeApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll_worker();
        egui::CentralPanel::default().show(ctx, |ui| {
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
                    [ui.available_width() - 90.0, 24.0],
                    egui::TextEdit::singleline(&mut display).interactive(false),
                );
                if ui.button("Browse").clicked() {
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
            ui.horizontal(|ui| {
                ui.label("Target size (MB)");
                ui.add(egui::DragValue::new(&mut self.target_mb).range(0.001..=100_000.0));
            });

            ui.add_space(8.0);
            ui.label("Output path");
            ui.horizontal(|ui| {
                ui.add_sized(
                    [ui.available_width() - 90.0, 24.0],
                    egui::TextEdit::singleline(&mut self.output),
                );
                if ui.button("Browse").clicked() {
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
            let can_compress = valid_input
                && self.ghostscript_error.is_none()
                && self.worker.is_none();
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
                        ui.label("Compressing your PDF…");
                    });
                    ctx.request_repaint_after(Duration::from_millis(100));
                }
                Status::Success(summary, path, _) if summary.met_target => {
                    ui.label(format!(
                        "Saved {:.2} MB at {} DPI to {}",
                        summary.size_bytes as f64 / 1_000_000.0,
                        summary.dpi,
                        path.display()
                    ));
                }
                Status::Success(summary, path, requested_target) => {
                    ui.label(format!(
                        "This PDF could not reach the {:.2} MB target without severe quality loss. The smallest result ({:.2} MB) was saved to {}.",
                        requested_target,
                        summary.size_bytes as f64 / 1_000_000.0,
                        path.display()
                    ));
                }
                Status::Failure(error) => {
                    ui.colored_label(egui::Color32::RED, error);
                }
            }
        });
    }
}

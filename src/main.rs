mod compress;
mod gs;
mod gui;

fn main() {
    if std::env::args_os().len() == 1 {
        if let Err(error) = gui::run() {
            eprintln!("Could not open PDF Squeeze: {error}");
            std::process::exit(1);
        }
    }
}

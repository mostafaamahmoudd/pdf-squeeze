#[cfg(windows)]
fn main() {
    println!("cargo:rerun-if-changed=assets/icons/pdf-squeeze.ico");
    winres::WindowsResource::new()
        .set_icon("assets/icons/pdf-squeeze.ico")
        .compile()
        .expect("Could not embed the Windows application icon");
}

#[cfg(not(windows))]
fn main() {}

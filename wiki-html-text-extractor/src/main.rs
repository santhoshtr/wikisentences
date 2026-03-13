use clap::{Parser, Subcommand};
use wiki_html_text_extractor::{WikiPage, get_text};
use serde::{Deserialize, Serialize};
use std::io::{self, BufRead, BufWriter, Write};

#[derive(Parser, Debug)]
#[command(author, version, about = "Extract plain text from Wikipedia HTML")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand, Debug)]
enum Command {
    /// Fetch a Wikipedia article by language/title and print extracted text
    Fetch {
        /// Wikipedia language code (e.g. "en", "ml")
        #[arg(short, long)]
        language: String,
        /// Wikipedia article title
        #[arg(short, long)]
        title: String,
        /// Output format: text or json
        #[arg(short, long, default_value = "text")]
        format: String,
    },
    /// Read line-delimited JSON from stdin, write extracted text as line-delimited JSON to stdout.
    /// Input line: {"id": 123, "url": "...", "name": "...", "html": "..."}
    /// Output line: {"id": 123, "url": "...", "name": "...", "text": "..."}
    Stdin,
}

#[derive(Deserialize)]
struct InputRecord {
    id: i64,
    url: String,
    name: String,
    html: String,
}

#[derive(Serialize)]
struct OutputRecord {
    id: i64,
    url: String,
    name: String,
    text: String,
}

#[tokio::main]
async fn main() -> io::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Command::Fetch { language, title, format } => {
            let segments = get_text(&language, &title).await.unwrap();
            let stdout = io::stdout();
            let mut handle = stdout.lock();
            match format.as_str() {
                "json" => {
                    let json_output = serde_json::to_string_pretty(&segments).unwrap();
                    writeln!(handle, "{}", json_output)?;
                }
                _ => {
                    for segment in segments {
                        writeln!(handle, "{}", segment)?;
                    }
                }
            }
        }

        Command::Stdin => {
            let stdin = io::stdin();
            let stdout = io::stdout();
            let mut out = BufWriter::new(stdout.lock());
            let mut page = WikiPage::new().expect("Failed to init WikiPage");

            for line in stdin.lock().lines() {
                let line = line?;
                let line = line.trim();
                if line.is_empty() {
                    continue;
                }
                let record: InputRecord = match serde_json::from_str(line) {
                    Ok(r) => r,
                    Err(e) => {
                        eprintln!("Skipping invalid JSON line: {e}");
                        continue;
                    }
                };

                let text = match page.extract_text(record.html) {
                    Ok(segments) => segments
                        .iter()
                        .map(|s| s.text.trim())
                        .filter(|t| !t.is_empty())
                        .collect::<Vec<_>>()
                        .join("\n\n"),
                    Err(e) => {
                        eprintln!("Failed to extract text for id={}: {e}", record.id);
                        String::new()
                    }
                };

                let output = OutputRecord {
                    id: record.id,
                    url: record.url,
                    name: record.name,
                    text,
                };
                let json = serde_json::to_string(&output).unwrap();
                out.write_all(json.as_bytes())?;
                out.write_all(b"\n")?;
            }
            out.flush()?;
        }
    }

    Ok(())
}

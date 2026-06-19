import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_bootstrap import Bootstrap5
from werkzeug.utils import secure_filename

from forms import RagForm1PDF, RagForm2
from rag_pipeline import RagDatabase, RagQuery
from openai import OpenAIError
from chromadb.errors import ChromaError


# Load environment variables
load_dotenv()

# Create app
app = Flask(__name__)
bootstrap = Bootstrap5(app)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['UPLOAD_FOLDER'] = os.getenv("TEMP_FOLDER")
csrf = CSRFProtect(app)

# Temp folder path
TEMP_FOLDER = os.environ.get('TEMP_FOLDER_PATH')


# Utility functions
def delete_temp_file_manual():
    for file in os.listdir(TEMP_FOLDER):
        os.remove(os.path.join(TEMP_FOLDER, file))


def get_rag_options():
    """Returns a list of tuples, extracted from the folder names in chroma db folder,
    to be used as options for a Flask Form select field"""
    chroma_db_path_rel = os.environ.get('CHROMA_PATH')
    chroma_db_path_abs = os.path.abspath(chroma_db_path_rel)
    rag_options = [('', 'Select a document')]

    for folder in os.listdir(chroma_db_path_abs):
        folder_path = os.path.join(chroma_db_path_abs, folder)

        if os.path.isdir(folder_path):
            folder_name = folder.replace("chroma_", "")
            folder_display_title = folder_name.replace("_", " ")
            rag_options.append((folder_name, folder_display_title))

    return rag_options


# Function for building a rag database from an uploaded document
@app.route('/', methods=["POST", "GET"])
def rag_setup_pdf():
    form = RagForm1PDF()
    if form.validate_on_submit():
        document = form.document_name.data
        document_description = form.document_description.data
        uploaded_file = form.file.data

        # Secure file name
        secured_filename = secure_filename(uploaded_file.filename)

        print(TEMP_FOLDER)

        # Save file into temp folder
        temp_dir = os.path.join(TEMP_FOLDER, secured_filename)
        uploaded_file.save(temp_dir)

        # Set RAG for uploaded file
        rag_database = RagDatabase(TEMP_FOLDER, document, file_type=".pdf")
        rag_database.add_manual_description(document_description)
        rag_database.prepare()

        # clear temp folder after processing
        delete_temp_file_manual()

        return redirect(url_for('rag_action'))

    return render_template("RAG.html", form=form)


# Function for getting answers from a RAG database and sending it to jinja for displaying
@app.route('/RAG-results', methods=["GET", "POST"])
def rag_action():
    form = RagForm2(rag_options=get_rag_options())

    # initialize all template variables
    response = None
    ready_sources = None
    prompt = None
    context = None

    # extensions of files that can be processed
    pdf_extension = ".pdf"
    md_extension = ".md"

    if form.validate_on_submit():
        document = form.selected_document.data
        query = form.query.data
        number_of_sources = int(form.number_of_sources.data)
        try:
            rag = RagQuery(document, number_of_contexts=number_of_sources)
            result = rag.get_response(query, number_of_contexts=number_of_sources)

            if result is None:
                flash("No relevant passages found in that document.", "main_error")
                return redirect(url_for("rag_action"))

            # unpack on success
            response = result["response"]
            sources = result["sources"]
            prompt = result["prompt"]
            context = result["context"]

            ready_sources = []

            for source in sources:
                if pdf_extension in source[0]:
                    source_main = (source[0].split("\\")[-1]
                                   .replace("-", " ")
                                   .replace("_", " ")
                                   .replace(pdf_extension, "")
                                   .title())
                    source_second = source[1]
                    ready_sources.append({"main": source_main, "specific": source_second, "file_type": pdf_extension})
                elif md_extension in source[0]:
                    source_main = (source[0].split("\\")[-1]
                                   .replace("-", " ")
                                   .replace("_", " ")
                                   .replace(md_extension, "")
                                   .title())
                    source_second = source[1]
                    ready_sources.append({"main": source_main, "specific": source_second, "file_type": md_extension})

        except KeyError as e:
            logging.critical("Missing environment var: %s", e, exc_info=True)
            flash("Server misconfiguration. Please contact support.", "main_error")
            return redirect(url_for("rag_action"))

        except ValueError as e:
            flash(str(e), "main_error")
            return redirect(url_for("rag_action"))

        except (ChromaError, OpenAIError, ConnectionError) as e:
            logging.error("Upstream error in RAG: %s", e, exc_info=True)
            flash("Service temporarily unavailable. Please try again later.", "main_error")
            return redirect(url_for("rag_action"))

        except Exception as e:
            logging.exception("Unexpected error in rag_action")
            flash(f'An unexpected <a title="{e}">error</a> occurred. Please try again.', 'main_error')
            return redirect(url_for("rag_action"))

    # GET or POST-with-errors just falls through here
    return render_template(
        "RAG-results.html",
        form=form,
        response=response,
        sources=ready_sources,
        prompt=prompt,
        context=context,
        pdf_extension=pdf_extension,
        md_extension=md_extension,
        zip=zip,
        enumerate=enumerate
    )


@app.route("/get_description", methods=["POST"])
def get_description():
    """Fetches the description given to the chroma db containing vectors and embeddings for the document provided"""
    document = request.json.get("doc_name")
    if not document:
        return jsonify({"error": "No document name provided"}), 400

    # Get the document descriptions
    rag = RagQuery(document_name=document)
    description = rag.get_document_descriptions()

    return jsonify({"description": description})


if __name__ == "__main__":
    app.run(debug=True)

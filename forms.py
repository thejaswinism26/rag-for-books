from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, SelectField, TextAreaField, IntegerField, validators
from flask_wtf.file import FileAllowed, FileRequired


class RagForm1PDF(FlaskForm):
    document_name = StringField("Which document are we setting up for RAG?")
    document_description = TextAreaField("What is the document about?")
    file = FileField('File Field', validators=[
        FileRequired(), FileAllowed(['pdf'],
                                    'Only PDFs can be uploaded!')])
    submit = SubmitField('Process File', render_kw={'class': 'button-form'})


class RagForm2(FlaskForm):
    selected_document = SelectField("Select a preset document to get answers from")
    query = TextAreaField('Query', validators=[
        validators.InputRequired(message="Please ask a question about the document uploaded.")],
        render_kw={"placeholder": "Ask a question about the provided document"})
    number_of_sources = IntegerField(
        'Number of sources',
        default=3,
        validators=[validators.NumberRange(
            3, 10, "Number of colors to extract should be between 3 and 20.")],
        render_kw={"class": "short-input"})
    submit = SubmitField('Get RAG answer', render_kw={'class': 'button-form'})

    def __init__(self, rag_options=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rag_options = rag_options or []
        self.selected_document.choices = self.rag_options

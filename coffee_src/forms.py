from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, FieldList, FormField

def dynamic_form(schema):
    class DForm(FlaskForm):
        name = StringField('static field')
        submit = SubmitField('RUN')
    for i, row in schema.iterrows():
        setattr(DForm, row['name'], StringField(row['name']))
    return DForm

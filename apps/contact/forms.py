from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        min_length=2,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Your name",
                "maxlength": 100,
            }
        ),
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "your@email.com",
                "maxlength": 254,
            }
        ),
    )
    message = forms.CharField(
        max_length=1000,
        min_length=10,
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Your question or feedback...",
                "maxlength": 1000,
            }
        ),
    )

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_email(self):
        return self.cleaned_data["email"].strip()

    def clean_message(self):
        return self.cleaned_data["message"].strip()
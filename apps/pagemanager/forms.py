from django import forms

from apps.producttest.models import Employee

from .models import FacebookPage, PagePost


def _employee_label(emp):
    return emp.nickname or emp.name


def _login_linked_employees():
    """Only employees with a linked login account can be assigned as page/post owners —
    visibility scoping (visible_pages) resolves through request.user.employee."""
    return Employee.objects.filter(is_active=True, user__isnull=False)


class FacebookPageForm(forms.ModelForm):
    class Meta:
        model = FacebookPage
        fields = ["page_name", "page_id", "status", "owners", "note"]
        widgets = {
            "page_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "เช่น กระดาษ 001"}),
            "page_id": forms.TextInput(attrs={
                "class": "form-control", "inputmode": "numeric",
                "placeholder": "กรอกตัวเลข ID Page", "id": "id_page_id",
            }),
            "status": forms.Select(attrs={"class": "form-select fw-bold"}),
            "owners": forms.CheckboxSelectMultiple(),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owners"].queryset = _login_linked_employees()
        self.fields["owners"].label_from_instance = _employee_label
        self.fields["owners"].required = False
        self.fields["note"].required = False


class PagePostForm(forms.ModelForm):
    class Meta:
        model = PagePost
        fields = [
            "image", "poster", "product_code", "product_name", "media_type",
            "post_id", "post_date", "note", "supervisor_note",
        ]
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control form-control-sm", "accept": "image/*"}),
            "poster": forms.Select(attrs={"class": "form-select"}),
            "product_code": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "เช่น SP001",
                "autocomplete": "off", "id": "id_product_code",
            }),
            "product_name": forms.HiddenInput(attrs={"id": "id_product_name"}),
            "media_type": forms.Select(attrs={"class": "form-select"}),
            "post_id": forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric", "placeholder": "ID POST"}),
            # format="%Y-%m-%d" prevents Thai locale from breaking <input type="date">
            "post_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "supervisor_note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, is_supervisor=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["poster"].queryset = _login_linked_employees()
        self.fields["poster"].label_from_instance = _employee_label
        self.fields["poster"].required = False
        self.fields["image"].required = False
        self.fields["media_type"].required = False
        self.fields["note"].required = False
        self.fields["supervisor_note"].required = False
        if not is_supervisor:
            self.fields.pop("supervisor_note")

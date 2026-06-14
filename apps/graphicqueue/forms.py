from django import forms
from apps.producttest.models import Employee
from .models import GraphicJob, MediaType


class GraphicJobForm(forms.ModelForm):
    class Meta:
        model = GraphicJob
        fields = [
            "sku", "name", "image",
            "urgency", "product_type",
            "assignee",
            "order_date", "deadline",
            "status", "submit_date", "work_url",
        ]
        widgets = {
            "sku": forms.TextInput(attrs={"class": "form-control", "placeholder": "เช่น SKU-001"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "ชื่อสินค้า"}),
            "image": forms.FileInput(attrs={"class": "form-control form-control-sm", "accept": "image/*"}),
            "urgency": forms.Select(attrs={"class": "form-select fw-bold"}),
            "product_type": forms.Select(attrs={"class": "form-select"}),
            "assignee": forms.Select(attrs={"class": "form-select fw-bold"}),
            # format="%Y-%m-%d" prevents Thai locale from breaking <input type="date">
            "order_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs={"class": "form-select fw-bold"}),
            "submit_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "work_url": forms.TextInput(attrs={"class": "form-control", "placeholder": "เช่น Google Drive หรือ file:///..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = Employee.objects.filter(
            is_graphic=True, is_active=True
        )
        self.fields["assignee"].empty_label = "-- เลือกผู้รับผิดชอบ --"
        self.fields["image"].required = False
        self.fields["submit_date"].required = False
        self.fields["work_url"].required = False


class MediaTypeForm(forms.ModelForm):
    class Meta:
        model = MediaType
        fields = ["name", "category"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "ชื่อประเภทสื่อใหม่..."}),
            "category": forms.Select(attrs={"class": "form-select form-select-sm"}),
        }

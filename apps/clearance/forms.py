from django import forms
from .models import ClearanceProduct


class ClearanceProductForm(forms.ModelForm):
    class Meta:
        model = ClearanceProduct
        fields = [
            "product_code",
            "product_name",
            "status",
            "assignee",
            "date_added",
            "process_date",
            "done_date",
            "unit_cost",
        ]
        widgets = {
            "product_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "เช่น SP001",
                    "autocomplete": "off",
                    "id": "id_product_code",
                }
            ),
            # product_name cached from JST on save — hidden so it travels with form submission
            "product_name": forms.HiddenInput(attrs={"id": "id_product_name"}),
            "status": forms.Select(attrs={"class": "form-select fw-bold"}),
            "assignee": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "เช่น เดือน, ฟลุ๊ค"}
            ),
            # format="%Y-%m-%d" required when LANGUAGE_CODE='th' to avoid Thai locale in date inputs
            "date_added": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "process_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "done_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "unit_cost": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "0.00", "step": "0.01", "min": "0"}
            ),
        }

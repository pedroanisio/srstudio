"""What test_stick_shop.py shares with other test modules."""

from srstudio import stick, stick_shop

SCREENS = (
    stick_shop.Screen(0.0, "Place item in the bagging area"),
    stick_shop.Screen(1.0, "Unexpected item in the bagging area", "error"),
    stick_shop.Screen(2.0, "Employee of the month", "award", face=stick.Look(apron="#2f7d57")),
)

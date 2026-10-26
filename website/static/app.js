(function () {
  "use strict";

  var MAX_TITLE = 200;
  var MAX_IMAGE = 2 * 1024 * 1024;
  var IMAGE_TYPES = ["png", "jpg", "jpeg", "gif", "webp"];
  var EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/;
  var EMAIL_INVALID = "Enter a valid email address (like name@gmail.com)";

  var REQUIRED = {
    register: {
      name: "Name is required",
      email: "Email is required",
      password: "Password is required",
      confirm_password: "Confirm password is required"
    },
    login: {
      email: "Email is required",
      password: "Password is required"
    },
    author: {
      name: "Name is required",
      country: "Country is required"
    },
    book: {
      price: "Price is required",
      author_id: "Author is required"
    },
    todo: {}
  };

  function showError(form, name, message) {
    var input = form.elements[name];
    var box = form.querySelector('[data-error-for="' + name + '"]');
    if (box) box.textContent = message || "";
    var field = input && input.closest ? input.closest(".field") : null;
    if (field) field.classList.toggle("has-error", !!message);
  }

  function checkForm(form) {
    var kind = form.getAttribute("data-validate");
    var errors = {};
    var required = REQUIRED[kind] || {};

    Object.keys(required).forEach(function (name) {
      var input = form.elements[name];
      if (input && input.value.trim() === "") errors[name] = required[name];
    });

    if ((kind === "register" || kind === "login") && !errors.email &&
        !EMAIL_PATTERN.test(form.elements.email.value.trim())) {
      errors.email = EMAIL_INVALID;
    }

    if (kind === "register" && !errors.confirm_password && !errors.password &&
        form.elements.password.value !== form.elements.confirm_password.value) {
      errors.confirm_password = "Passwords do not match";
    }

    var title = form.querySelector('[data-rule="title"]');
    if (title) {
      var t = title.value.trim();
      if (t === "") errors[title.name] = "Title is required";
      else if (t.length > MAX_TITLE) errors[title.name] = "Title is too long (200 characters at most)";
    }

    var price = form.querySelector('[data-rule="price"]');
    if (price && !errors.price) {
      var p = Number(price.value);
      if (isNaN(p)) errors.price = "Price must be a number";
      else if (p < 0 || p >= 100000000) errors.price = "Price must be between 0 and 99999999.99";
    }

    form.querySelectorAll('[data-rule="image"]').forEach(function (input) {
      var file = input.files && input.files[0];
      if (!file) return;
      var ext = file.name.split(".").pop().toLowerCase();
      if (IMAGE_TYPES.indexOf(ext) === -1) errors[input.name] = "Image must be a PNG, JPG, GIF or WEBP file";
      else if (file.size > MAX_IMAGE) errors[input.name] = "The image is too big (2 MB at most)";
    });

    form.querySelectorAll("[data-error-for]").forEach(function (box) {
      showError(form, box.getAttribute("data-error-for"), errors[box.getAttribute("data-error-for")]);
    });
    return Object.keys(errors).length === 0;
  }

  document.querySelectorAll("form[data-validate]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!checkForm(form)) {
        e.preventDefault();
        var bad = form.querySelector(".has-error input, .has-error select");
        if (bad) bad.focus();
      }
    });
  });

  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  document.querySelectorAll('input[type="file"][data-rule="image"]').forEach(function (input) {
    input.addEventListener("change", function () {
      var preview = input.parentElement.querySelector(".preview");
      var file = input.files && input.files[0];
      if (!preview) return;
      if (file && file.type.indexOf("image/") === 0) {
        preview.src = URL.createObjectURL(file);
        preview.hidden = false;
      } else {
        preview.hidden = true;
      }
    });
  });

  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var root = document.documentElement;
      var current = root.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  setTimeout(function () {
    document.querySelectorAll(".alert-success").forEach(function (el) {
      el.classList.add("fade");
    });
  }, 3500);
})();

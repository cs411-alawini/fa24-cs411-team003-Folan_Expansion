document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('login-form');

  loginForm.addEventListener('submit', function(event) {
    event.preventDefault();
    const usernameOrEmail = document.getElementById('usernameOrEmail').value;
    const password = document.getElementById('password').value;

    fetch('/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username_or_email: usernameOrEmail, password: password })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Redirect to the main page
        window.location.href = 'frontend.html';
      } else {
        alert('Login failed: ' + data.error);
      }
    })
    .catch(error => console.error('Error:', error));
  });
});
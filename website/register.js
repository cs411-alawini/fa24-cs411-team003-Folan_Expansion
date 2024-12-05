document.addEventListener('DOMContentLoaded', () => {
  const registerForm = document.getElementById('register-form');

  registerForm.addEventListener('submit', function(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    // Check if email is a Gmail address
    if (!email.endsWith('@gmail.com')) {
      alert('Please use a Gmail address.');
      return;
    }

    fetch('/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username, email: email, password: password })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        alert('Registration successful! Please log in.');
        window.location.href = 'login.html';
      } else {
        alert('Registration failed: ' + data.error);
      }
    })
    .catch(error => console.error('Error:', error));
  });
});
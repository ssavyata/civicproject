
  function togglePassword() {
    const input = document.getElementById('id_password');
    const icon  = document.getElementById('pwd-icon');
    input.type = input.type === 'password' ? 'text' : 'password';
    icon.textContent = input.type === 'password' ? 'visibility' : 'visibility_off';
  }

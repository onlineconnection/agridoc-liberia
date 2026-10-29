function togglePassword(fieldId) {
    const input = document.getElementById(fieldId);
    const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);
    const icon = input.nextElementSibling?.querySelector('svg');

    if (icon) {
        icon.style.transform = type === 'password' ? 'rotate(180deg)' : 'rotate(0deg)';
    }
}

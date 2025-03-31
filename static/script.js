// Функция для отображения сообщений
function showMessage(elementId, message, isError = false) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = isError ? 'error' : 'success';
}

// Функция для отображения JSON
function showJSON(elementId, data) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

// Функция для отображения токена
function showToken() {
    const token = localStorage.getItem('token');
    document.getElementById('tokenDisplay').value = token || '';
}

// Проверка, авторизован ли пользователь
function checkAuth() {
    const token = localStorage.getItem('token');
    const logoutButton = document.getElementById('logoutButton');
    if (token) {
        logoutButton.disabled = false;
    } else {
        logoutButton.disabled = true;
    }
    showToken();
}

// Обработка формы авторизации
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem('token', data.token);
            showMessage('loginMessage', 'Login successful!', false);
            checkAuth();
        } else {
            showMessage('loginMessage', data.error || 'Login failed', true);
        }
    } catch (error) {
        showMessage('loginMessage', 'Error: ' + error.message, true);
    }
});

// Запрос к защищенному ресурсу
document.getElementById('getContent').addEventListener('click', async () => {
    const token = localStorage.getItem('token');
    if (!token) {
        showMessage('contentMessage', 'Please login first', true);
        return;
    }

    try {
        const response = await fetch('/api/content', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,  // Add Bearer prefix
            },
        });

        const data = await response.json();

        if (response.ok) {
            showJSON('contentMessage', data);
        } else {
            showMessage('contentMessage', data.error || 'Failed to fetch content', true);
        }
    } catch (error) {
        showMessage('contentMessage', 'Error: ' + error.message, true);
    }
});

// Обработка выхода
document.getElementById('logoutButton').addEventListener('click', async () => {
    const token = localStorage.getItem('token');
    if (!token) {
        showMessage('logoutMessage', 'No token found', true);
        return;
    }

    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,  // Add Bearer prefix
            },
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.removeItem('token');
            showMessage('logoutMessage', 'Logout successful!', false);
            checkAuth();
        } else {
            showMessage('logoutMessage', data.error || 'Logout failed', true);
        }
    } catch (error) {
        showMessage('logoutMessage', 'Error: ' + error.message, true);
    }
});

// Проверяем авторизацию при загрузке страницы
checkAuth();
    //============================================================================================================
    //=============================================================================================================
    //============================================================================================================
    //=============================================================================================================
    //                                            PHẦN GIỎ HÀNG


function addToCart(event, id, name, price, quantity = 1) {
    event.preventDefault();

    fetch('/api/add-cart', {
        method: 'post',
        body: JSON.stringify({
            id: id,
            name: name,
            price: price,
            quantity: quantity   // Thêm dòng này
        }),
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert(data.error); // hoặc redirect tới trang login
        } else {
            let counters = document.getElementsByClassName('cart-counter');
            for (let c of counters) {
        c.innerText = data.total_items; // ✅ Gán đúng số mặt hàng
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function addAllToCart() {
    if (!productsToRebuy || productsToRebuy.length === 0) {
        alert("Không có sản phẩm để mua lại");
        return;
    }

    productsToRebuy.forEach(p => {
        addToCart({ preventDefault: () => {} }, p.id, p.name, p.price, p.quantity);
    });

    alert("✅ Đã thêm tất cả vào giỏ!");
}


function updateCart(id, inputElement) {
    const quantity = parseInt(inputElement.value);
    if (isNaN(quantity) || quantity < 1) {
        inputElement.value = 1;
        return;
    }

    fetch('/api/update-cart', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            id: id,
            quantity: quantity
        })
    })
    .then(res => res.json())
    .then(data => {
        // ✅ Cập nhật số lượng tổng giỏ hàng (ở header/menu)
        document.querySelectorAll('.cart-counter').forEach(el => {
             el.innerText = data.total_items; // ✅ Dùng số mặt hàng khác nhau
        });

        // ✅ Cập nhật tổng tiền toàn bộ giỏ
        const amountEl = document.getElementById('total-amount');
        if (amountEl)
            amountEl.innerText = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 0 }).format(data.total_amount) + ' VND';

        // ✅ Cập nhật thành tiền dòng sản phẩm
        const priceEl = document.getElementById(`product-price-${id}`);
        const price = parseInt(priceEl?.innerText?.replace(/[^0-9]/g, '')) || 0;

        const productTotalEl = document.getElementById(`product-total-${id}`);
        if (productTotalEl)
            productTotalEl.innerText = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price * quantity);

        // ✅ Cập nhật lại checkbox (nếu đang được chọn) để tính tổng tiền chọn
const cb = document.querySelector(`.cart-checkbox[data-product-id='${id}']`);
        if (cb) {
    cb.setAttribute('data-quantity', quantity);  // <- đảm bảo cập nhật đúng DOM
}

        updateSelectedTotals(); // tính lại tổng tiền chọn nếu có
    }
    )
    .catch(err => console.error('Lỗi updateCart:', err));
}



// chekcbox để chọn từng sản phẩm trong giỏ hàng
function toggleCheckbox(cb) {
    const cartId = cb.dataset.cartId;
    const isChecked = cb.checked;

    fetch('/api/toggle-select-cart-item', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            cart_id: cartId,
            is_selected: isChecked
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            updateSelectedTotals(); // Cập nhật lại tổng tiền, số lượng
        } else {
            alert('Cập nhật trạng thái thất bại!');
        }
    })
    .catch(err => console.error('Lỗi khi gửi checkbox:', err));
}


// chekcbox để chọn all sản phẩm trong giỏ hàng
function toggleSelectAll(masterCheckbox) {
    const allCheckboxes = document.querySelectorAll('.cart-checkbox');
    const isChecked = masterCheckbox.checked;

    const cartIds = Array.from(allCheckboxes).map(cb => cb.dataset.cartId);

    // ✅ Đánh dấu checked trên UI
    allCheckboxes.forEach(cb => {
        cb.checked = isChecked;
    });

    // ✅ Gửi request lưu trạng thái tất cả xuống DB
    fetch('/api/toggle-select-all-cart-items', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            cart_ids: cartIds,
            is_selected: isChecked
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            updateSelectedTotals();
        } else {
            alert('Cập nhật chọn tất cả thất bại');
        }
    })
    .catch(err => console.error('Lỗi toggleSelectAll:', err));
}



//hàm xóa sản phẩm trong giỏ hàng
function deleteCart(id) {
    if (confirm("Bạn chắc chắn muốn xóa sản phẩm này không ??")) {
        fetch('/api/delete-cart/' + id, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(res => res.json())
        .then(data => {
            // Xoá thành công → reload lại trang để cập nhật toàn bộ
            location.reload();
        })
        .catch(err => {
            console.error(err);
            alert("Có lỗi xảy ra khi xoá sản phẩm.");
        });
    }
}



// ✅Hàm cập nhật giỏ hàng khi thay đổi số lượng
function updateSelectedTotals() {
  const checkboxes = document.querySelectorAll('.cart-checkbox');
  let totalItems = 0;   // ✅ Đếm số mặt hàng (checkbox được tick)
  let totalAmount = 0;

  checkboxes.forEach(cb => {
      if (cb.checked) {
          totalItems++; // ✅ Mỗi ô tick = 1 mặt hàng
          const quantity = parseInt(cb.dataset.quantity) || 0;
          const price = parseFloat(cb.dataset.price) || 0;
          totalAmount += quantity * price;
      }
  });

  // ✅ Cập nhật số mặt hàng đã chọn
  const quantityElement = document.getElementById('selected-total-quantity');
  if (quantityElement) {
      quantityElement.innerText = totalItems.toString();
  }

  // ✅ Cập nhật tổng tiền
  const amountElement = document.getElementById('selected-total-amount');
  if (amountElement) {
      amountElement.textContent = totalAmount.toLocaleString('vi-VN', { maximumFractionDigits: 0 }) + ' VND';
  }
}

// ✅ Hàm cập nhật giỏ hàng khi thay đổi số lượng
function changeQuantity(productId, delta) {
    const input = document.getElementById('quantity-display-' + productId);
    let currentValue = parseInt(input.value) || 1;
    let newValue = currentValue + delta;
    if (newValue < 1) newValue = 1;
    input.value = newValue;
    updateCart(productId, input);
}

// ✅ Hàm cập nhật giỏ hàng
function validateQuantity(input) {
    let val = input.value.replace(/[^0-9]/g, '');
    if (val === '' || parseInt(val) < 1) val = '1';
    input.value = val;
}

// ✅ Hàm load lai giỏ hàng
  window.onload = function () {
    updateSelectedTotals();
};







    //============================================================================================================
    //=============================================================================================================
    //============================================================================================================
    //=============================================================================================================
    //                     PHẦN ĐỊA CHỈ TRONG MODAL THANH TOÁN



    // ✅ Trạng thái

    let selectedProvince = null, selectedDistrict = null, selectedWard = null, currentTab = 'province';
    let isEditing = false;

    // ✅ Biến toàn cục
    let editingAddressId = null;

    // ✅ Hàm: Mở modal THÊM hoặc SỬA ĐỊA CHỈ
    function openEditAddressModal(editing, id) {
      isEditing = editing;
      editingAddressId = editing ? id : null;

      document.getElementById('editAddressModal').classList.add('active');

      // ✅ ĐỔI TIÊU ĐỀ
      const title = document.getElementById('editAddressModalTitle');
      title.textContent = editing ? 'Sửa Địa Chỉ' : 'Thêm Địa Chỉ Mới';

      if (editing) {
        const checked = id
          ? document.querySelector(`input[value="${id}"]`)
          : document.querySelector('input[name="addressOption"]:checked');

        if (checked) {
          document.getElementById('editName').value = checked.dataset.name || '';
          document.getElementById('editPhone').value = checked.dataset.phone || '';
          selectedProvince = { name_with_type: checked.dataset.province };
          selectedDistrict = { name_with_type: checked.dataset.district };
          selectedWard = { name_with_type: checked.dataset.ward };
          document.getElementById('editSpecificAddress').value = checked.dataset.line || '';
        }
      } else {
        editingAddressId = null;
        document.getElementById('editName').value = '';
        document.getElementById('editPhone').value = '';
        selectedProvince = selectedDistrict = selectedWard = null;
        document.getElementById('editSpecificAddress').value = '';
      }

      updateAddressResult();
    }

    function updateAddressResult() {
      const btn = document.getElementById('addressResult');
      const parts = [];
      if (selectedProvince) parts.push(selectedProvince.name_with_type);
      if (selectedDistrict) parts.push(selectedDistrict.name_with_type);
      if (selectedWard) parts.push(selectedWard.name_with_type);

      btn.textContent = parts.length > 0
        ? parts.join(', ') + ' ⌵'
        : 'Chọn Tỉnh/Thành phố, Quận/Huyện, Phường/Xã ⌵';

      // ✅ Reset viền khi đã chọn xong
      if (selectedProvince) document.getElementById('provinceDropdown').style.border = '1px solid #ccc';
      if (selectedDistrict) document.getElementById('districtDropdown').style.border = '1px solid #ccc';
      if (selectedWard) document.getElementById('wardDropdown').style.border = '1px solid #ccc';
    }


    // ✅ Hàm: Mở modal CHỌN ĐỊA CHỈ
    function openAddressModal() {
      closeAllModals();
      document.getElementById('addressModal').classList.add('active');
    }

    // ✅ Hàm: Đóng tất cả modal
    function closeAllModals() {
      document.getElementById('addressModal').classList.remove('active');
      document.getElementById('editAddressModal').classList.remove('active');
    }

    // ✅ Hàm: Đóng modal CHỌN ĐỊA CHỈ
    function closeAddressModal() {
      document.getElementById('addressModal').classList.remove('active');
    }

    // ✅ Hàm: Đóng modal SỬA ĐỊA CHỈ
    function closeEditAddressModal() {
      document.getElementById('editAddressModal').classList.remove('active');
      if (isEditing) {
        document.getElementById('addressModal').classList.add('active');
      }
    }

 // ✅ Hàm: Xác nhận địa chỉ chọn (chỉ đổi UI)
function confirmAddress() {
  const checked = document.querySelector('input[name="addressOption"]:checked');
  if (!checked) {
    alert('Vui lòng chọn địa chỉ!');
    return;
  }

  const name = checked.dataset.name || '';
  const phone = checked.dataset.phone || '';
  const province = checked.dataset.province || '';
  const district = checked.dataset.district || '';
  const ward = checked.dataset.ward || '';
  const line = checked.dataset.line || '';

  document.getElementById('userName').innerText = name;
  document.getElementById('phoneNumber').innerText = phone;
  document.getElementById('userAddress').innerText = `${line}, ${ward}, ${district}, ${province}`;
}

// ✅ Hàm: Set địa chỉ mặc định
function setDefaultAddress() {
  const checked = document.querySelector('input[name="addressOption"]:checked');
  if (!checked) {
    alert('Vui lòng chọn địa chỉ!');
    return;
  }

  fetch('/api/set-default-address', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address_id: checked.value })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      confirmAddress(); // chỉ update UI
      closeAddressModal(); // đóng modal luôn!
    } else {
      alert('Lỗi khi set địa chỉ mặc định!');
    }
  });
}


    // ✅ Hàm: Toggle dropdown Tỉnh/Huyện/Xã
    function toggleAddressTabs() {
      const box = document.getElementById('addressTabs');
      box.style.display = box.style.display === 'block' ? 'none' : 'block';
      if (box.style.display === 'block') switchTab(currentTab);
    }

    // ✅ Hàm: Chuyển tab Tỉnh/Huyện/Xã
    function switchTab(tab) {
      if (tab === 'district' && !selectedProvince) return;
      if (tab === 'ward' && !selectedDistrict) return;

      currentTab = tab;
      ['province', 'district', 'ward'].forEach(t => {
        document.getElementById('tab-' + t).classList.toggle('active', t === tab);
      });

      if (tab === 'province') loadProvinces();
      else if (tab === 'district') loadDistricts();
      else if (tab === 'ward') loadWards();

      updateTabStates();
    }

    // ✅ Hàm: Cập nhật trạng thái tab
    function updateTabStates() {
      const districtTab = document.getElementById('tab-district');
      const wardTab = document.getElementById('tab-ward');

      if (!selectedProvince) districtTab.classList.add('disabled');
      else districtTab.classList.remove('disabled');

      if (!selectedDistrict) wardTab.classList.add('disabled');
      else wardTab.classList.remove('disabled');
    }

    // ✅ Hàm: Load API Tỉnh
    async function loadProvinces() {
      let res = await fetch('/api/provinces');
      let data = await res.json();
      renderTabList(data, 'province');
      updateTabStates();
    }

    // ✅ Hàm: Load API Huyện
    async function loadDistricts() {
      let res = await fetch('/api/districts/' + selectedProvince.code);
      let data = await res.json();
      renderTabList(data, 'district');
      updateTabStates();
    }

    // ✅ Hàm: Load API Xã
    async function loadWards() {
      let res = await fetch('/api/wards/' + selectedDistrict.code);
      let data = await res.json();
      renderTabList(data, 'ward');
      updateTabStates();
    }

    // ✅ Hàm: Render danh sách trong tab
    function renderTabList(data, type) {
      const list = document.getElementById('tabList');
      list.innerHTML = '';
      data.forEach(item => {
        const div = document.createElement('div');
        div.textContent = item.name_with_type;
        div.onclick = () => selectItem(item, type);
        list.appendChild(div);
      });
    }

    // ✅ Hàm: Chọn item Tỉnh/Huyện/Xã
    function selectItem(item, type) {
      if (type === 'province') {
        selectedProvince = item;
        selectedDistrict = selectedWard = null;
        switchTab('district');
      } else if (type === 'district') {
        selectedDistrict = item;
        selectedWard = null;
        switchTab('ward');
      } else {
        selectedWard = item;
        document.getElementById('addressTabs').style.display = 'none';
      }
      updateAddressResult();
    }

    // ✅ Hàm: Lưu địa chỉ (thêm mới hoặc cập nhật)
    function saveAddress() {
      const nameInput = document.getElementById('editName');
      const phoneInput = document.getElementById('editPhone');
      const lineInput = document.getElementById('editSpecificAddress');

      const name = nameInput.value.trim();
      const phone = phoneInput.value.trim();
      const line = lineInput.value.trim();

      // ✅ Reset viền về bình thường
      nameInput.style.border = phoneInput.style.border = lineInput.style.border = '1px solid #ccc';

      let hasError = false;
       if (!validateInputs()) {
        return; // Dừng nếu không hợp lệ
    }

      if (!name) {
        nameInput.style.border = '1px solid red';
        hasError = true;
      }
      if (!phone) {
        phoneInput.style.border = '1px solid red';
        hasError = true;
      }
      if (!line) {
        lineInput.style.border = '1px solid red';
        hasError = true;
      }

    if (!selectedProvince) {
      document.getElementById('provinceDropdown').style.border = '1px solid red';
      hasError = true;
    }

    if (selectedProvince && !selectedDistrict) {
      document.getElementById('provinceDropdown').style.border = '1px solid red';
      hasError = true;
    }

    if (selectedProvince && selectedDistrict && !selectedWard) {
      document.getElementById('provinceDropdown').style.border = '1px solid red';
      hasError = true;
    }

      if (hasError) return;

      const url = editingAddressId ? '/api/update-address' : '/api/save-address';

      const payload = {
        receiver_name: name,
        receiver_phone: phone,
        receiver_province: selectedProvince.name_with_type,
        receiver_district: selectedDistrict.name_with_type,
        receiver_ward: selectedWard.name_with_type,
        receiver_address_line: line
      };

      if (editingAddressId) {
        payload.id = editingAddressId;
      }

      fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      }).then(res => res.json()).then(data => {
  if (data.success) {
    if (editingAddressId) {
      updateAddressItem({ id: editingAddressId, ...payload });
    } else {
      // Nếu muốn: thêm địa chỉ mới mà không F5 thì viết hàm addAddressItem(payload)
      location.reload(); // hoặc vẫn reload nếu chưa cần thêm mới động
    }
    closeEditAddressModal();
  } else {
    console.error('Lỗi:', data.error);
  }
});
    }

// ✅ Hàm: Xoá địa chỉ
    function deleteAddress() {
  if (!editingAddressId) {
    alert('Không có địa chỉ để xoá!');
    return;
  }

  if (!confirm('Bạn chắc chắn muốn xoá địa chỉ này?')) {
    return;
  }

  fetch('/api/delete-address', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ id: editingAddressId })
  }).then(res => res.json()).then(data => {
if (data.success) {
  removeAddressItem(editingAddressId);
  closeEditAddressModal();
} else {
      alert('Lỗi: ' + data.error);
    }
  });
}

// ✅ Hàm: Xoá phần tử địa chỉ trên HTML
function removeAddressItem(id) {
  const input = document.querySelector(`input[value="${id}"]`);
  if (input) {
    const label = input.closest('label.address-item');
    if (label) label.remove();
  }
}

// ✅ Hàm: Cập nhật phần tử địa chỉ trên HTML
function updateAddressItem(address) {
  const input = document.querySelector(`input[value="${address.id}"]`);
  if (input) {
    input.dataset.name = address.receiver_name;
    input.dataset.phone = address.receiver_phone;
    input.dataset.province = address.receiver_province;
    input.dataset.district = address.receiver_district;
    input.dataset.ward = address.receiver_ward;
    input.dataset.line = address.receiver_address_line;

    const label = input.closest('label.address-item');
    if (label) {
      label.querySelector('strong').innerText = address.receiver_name;
      label.querySelector('.address-line').innerText = address.receiver_address_line;
      label.querySelector('.address-region').innerText = `${address.receiver_ward}, ${address.receiver_district}, ${address.receiver_province}`;
    }
  }
}


// ✅ Auto check radio đầu tiên nếu chưa có cái nào được chọn
document.addEventListener('DOMContentLoaded', function () {
  const radios = document.querySelectorAll('input[name="addressOption"]');
  if (radios.length > 0 && ![...radios].some(r => r.checked)) {
    radios[0].checked = true;
  }
});






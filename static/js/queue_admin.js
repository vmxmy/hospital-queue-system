/**
 * 实现Django Admin中队列添加表单的科室-检查项目-设备联动功能
 */
(function($) {
    'use strict';
    $(document).ready(function() {
        // 确保在Django Admin环境中
        if (document.getElementById('queue_form')) {
            // 获取相关字段
            const departmentField = $('#id_department');
            const examinationField = $('#id_examination');
            const equipmentField = $('#id_equipment');
            
            console.log('科室-检查项目-设备联动初始化成功');
            
            // 初始状态：禁用检查项目和设备字段
            if (departmentField.val() === '') {
                examinationField.prop('disabled', true);
                equipmentField.prop('disabled', true);
            }
            
            if (examinationField.val() === '') {
                equipmentField.prop('disabled', true);
            }
            
            // 科室变更时，同时更新检查项目和设备下拉框
            departmentField.on('change', function() {
                const departmentId = $(this).val();
                examinationField.empty().append('<option value="">---------</option>');
                equipmentField.empty().append('<option value="">---------</option>');
                
                if (!departmentId) {
                    examinationField.prop('disabled', true);
                    equipmentField.prop('disabled', true);
                    return;
                }
                
                // 发起Ajax请求获取科室对应的检查项目
                $.ajax({
                    url: `/admin/navigation/queue/api/department/${departmentId}/examinations/`,
                    type: 'GET',
                    dataType: 'json',
                    success: function(data) {
                        console.log('获取检查项目成功:', data);
                        examinationField.prop('disabled', false);
                        
                        // 填充检查项目下拉框
                        $.each(data, function(index, item) {
                            examinationField.append(
                                $('<option></option>').attr('value', item.id).text(item.name)
                            );
                        });
                    },
                    error: function(xhr, status, error) {
                        console.error('获取检查项目失败:', error, xhr.responseText);
                        // 显示错误信息
                        $('.errornote').remove();
                        $('<p class="errornote">获取检查项目失败，请重试</p>')
                            .insertBefore(examinationField.closest('.form-row'));
                    }
                });
                
                // 发起Ajax请求获取科室对应的设备
                $.ajax({
                    url: `/admin/navigation/queue/api/department/${departmentId}/equipment/`,
                    type: 'GET',
                    dataType: 'json',
                    success: function(data) {
                        console.log('获取科室设备成功:', data);
                        equipmentField.prop('disabled', false);
                        
                        // 填充设备下拉框
                        if (data && data.length > 0) {
                            $.each(data, function(index, item) {
                                // 只添加状态为available的设备
                                if (item.status === 'available') {
                                    equipmentField.append(
                                        $('<option></option>').attr('value', item.id).text(item.name)
                                    );
                                }
                            });
                        } else {
                            // 没有设备可用时显示提示
                            equipmentField.append(
                                $('<option disabled></option>').text('没有可用设备')
                            );
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error('获取设备失败:', error, xhr.responseText);
                        // 显示错误信息
                        $('.errornote').remove();
                        $('<p class="errornote">获取科室设备失败，请重试</p>')
                            .insertBefore(equipmentField.closest('.form-row'));
                    }
                });
            });
            
            // 检查项目变更时，更新设备下拉框
            examinationField.on('change', function() {
                const examinationId = $(this).val();
                const departmentId = departmentField.val();
                
                if (!examinationId) {
                    // 仅在未选择检查项目时，使用科室的设备
                    if (departmentId) {
                        $.ajax({
                            url: `/admin/navigation/queue/api/department/${departmentId}/equipment/`,
                            type: 'GET',
                            dataType: 'json',
                            success: function(data) {
                                equipmentField.empty().append('<option value="">---------</option>');
                                equipmentField.prop('disabled', false);
                                
                                // 填充设备下拉框
                                if (data && data.length > 0) {
                                    $.each(data, function(index, item) {
                                        // 只添加状态为available的设备
                                        if (item.status === 'available') {
                                            equipmentField.append(
                                                $('<option></option>').attr('value', item.id).text(item.name)
                                            );
                                        }
                                    });
                                } else {
                                    equipmentField.append(
                                        $('<option disabled></option>').text('没有可用设备')
                                    );
                                }
                            },
                            error: function(xhr, status, error) {
                                console.error('获取设备失败:', error, xhr.responseText);
                            }
                        });
                    } else {
                        equipmentField.empty().append('<option value="">---------</option>');
                        equipmentField.prop('disabled', true);
                    }
                    return;
                }
                
                // 发起Ajax请求获取检查项目对应的设备
                $.ajax({
                    url: `/admin/navigation/queue/api/examination/${examinationId}/equipment/`,
                    type: 'GET',
                    dataType: 'json',
                    success: function(data) {
                        console.log('获取设备成功:', data);
                        equipmentField.empty().append('<option value="">---------</option>');
                        equipmentField.prop('disabled', false);
                        
                        // 填充设备下拉框
                        if (data && data.length > 0) {
                            $.each(data, function(index, item) {
                                // 添加所有状态为available的设备
                                equipmentField.append(
                                    $('<option></option>').attr('value', item.id).text(item.name)
                                );
                            });
                        } else {
                            // 没有设备可用时显示提示
                            equipmentField.append(
                                $('<option disabled></option>').text('没有可用设备')
                            );
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error('获取设备失败:', error, xhr.responseText);
                        // 显示错误信息
                        $('.errornote').remove();
                        $('<p class="errornote">获取设备失败，请重试</p>')
                            .insertBefore(equipmentField.closest('.form-row'));
                        
                        // 禁用设备字段
                        equipmentField.prop('disabled', true);
                    }
                });
            });
            
            // 如果初始有科室值，触发一次变更事件以加载检查项目和设备
            if (departmentField.val()) {
                departmentField.trigger('change');
                
                // 如果初始有检查项目值，触发一次变更事件以加载设备
                if (examinationField.val()) {
                    examinationField.trigger('change');
                }
            }
        }
    });
})(django.jQuery || jQuery); 
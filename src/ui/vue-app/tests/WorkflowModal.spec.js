import { mount } from '@vue/test-utils';
import WorkflowModal from '@/components/WorkflowModal.vue';
import axios from 'axios';

// Mock axios
jest.mock('axios');

describe('WorkflowModal.vue', () => {
  let wrapper;
  
  beforeEach(() => {
    // Reset mocks
    axios.get.mockReset();
    axios.put.mockReset();
    
    // Create wrapper
    wrapper = mount(WorkflowModal, {
      propsData: {
        show: true
      }
    });
  });
  
  it('displays workflows with custom names', async () => {
    // Mock API response
    const mockWorkflows = [
      { 
        name: 'Custom Workflow Name', 
        filename: 'workflow1.yaml', 
        description: 'Description 1',
        default_name: 'workflow1'
      },
      { 
        name: 'Another Workflow', 
        filename: 'workflow2.yaml', 
        description: 'Description 2',
        default_name: 'workflow2'
      }
    ];
    
    axios.get.mockResolvedValue({ data: mockWorkflows });
    
    // Trigger fetchWorkflows method
    await wrapper.vm.fetchWorkflows();
    
    // Wait for DOM to update
    await wrapper.vm.$nextTick();
    
    // Check that workflows are displayed with their custom names
    const workflowItems = wrapper.findAll('.workflow-item');
    expect(workflowItems.length).toBe(2);
    
    const firstWorkflowName = workflowItems.at(0).find('.workflow-name').text();
    expect(firstWorkflowName).toBe('Custom Workflow Name');
    
    const secondWorkflowName = workflowItems.at(1).find('.workflow-name').text();
    expect(secondWorkflowName).toBe('Another Workflow');
  });
  
  it('allows editing workflow names', async () => {
    // Mock API responses
    const mockWorkflows = [
      { 
        name: 'Original Name', 
        filename: 'workflow1.yaml', 
        description: 'Description',
        default_name: 'workflow1'
      }
    ];
    
    axios.get.mockResolvedValue({ data: mockWorkflows });
    axios.put.mockResolvedValue({ data: { success: true } });
    
    // Fetch workflows
    await wrapper.vm.fetchWorkflows();
    await wrapper.vm.$nextTick();
    
    // Click edit button
    const editButton = wrapper.find('.edit-button');
    await editButton.trigger('click');
    
    // Check that edit mode is active
    expect(wrapper.vm.editingWorkflow).toBe('workflow1.yaml');
    
    // Set new name
    const input = wrapper.find('.workflow-name-edit input');
    await input.setValue('Updated Name');
    
    // Click save button
    const saveButton = wrapper.find('.save-button');
    await saveButton.trigger('click');
    
    // Check that API was called with correct parameters
    expect(axios.put).toHaveBeenCalledWith(
      'http://localhost:8000/workflows/workflow1.yaml/name',
      { name: 'Updated Name' }
    );
    
    // Check that edit mode is exited
    expect(wrapper.vm.editingWorkflow).toBeNull();
    
    // Check that workflow name is updated in the local list
    expect(wrapper.vm.workflows[0].name).toBe('Updated Name');
  });
  
  it('cancels editing when cancel button is clicked', async () => {
    // Mock API response
    const mockWorkflows = [
      { 
        name: 'Original Name', 
        filename: 'workflow1.yaml', 
        description: 'Description',
        default_name: 'workflow1'
      }
    ];
    
    axios.get.mockResolvedValue({ data: mockWorkflows });
    
    // Fetch workflows
    await wrapper.vm.fetchWorkflows();
    await wrapper.vm.$nextTick();
    
    // Click edit button
    const editButton = wrapper.find('.edit-button');
    await editButton.trigger('click');
    
    // Set new name
    const input = wrapper.find('.workflow-name-edit input');
    await input.setValue('Updated Name');
    
    // Click cancel button
    const cancelButton = wrapper.find('.cancel-button');
    await cancelButton.trigger('click');
    
    // Check that edit mode is exited
    expect(wrapper.vm.editingWorkflow).toBeNull();
    
    // Check that workflow name is not updated
    expect(wrapper.vm.workflows[0].name).toBe('Original Name');
  });
});
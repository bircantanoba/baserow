import { mapGetters } from 'vuex'
import applicationContextMixin from '@baserow/modules/builder/mixins/applicationContext'
import { CurrentRecordDataProviderType } from '@baserow/modules/builder/dataProviderTypes'

export default {
  mixins: [applicationContextMixin],
  computed: {
    /**
     * Returns the schema which the service schema property selector
     * will use when listing the available properties. If the collection
     * element is not nested, we'll use the selected data source's schema,
     * otherwise if it's nested, we use the current record's data schema.
     * @returns {Object} - The schema to use.
     */
    propertySelectorSchema() {
      return this.$registry
        .get('builderDataProvider', CurrentRecordDataProviderType.getType())
        .getDataSchema({
          ...this.applicationContext,
          /**
           * We want to use the data_source_id of this element...
           */
          allowSameElement: true,
          /**
           * but, we don't want to use the schema property of this element as we are
           * defining it.
           */
          followSameElementSchemaProperties: false,
        })
    },
    /**
     * A convenience computed method which returns if this element has
     * a collection ancestor. This influences a few things, such as whether
     * the schema property selector is available, or whether the data source
     * dropdown is available.
     * @returns {boolean} - Whether the element has a collection ancestor.
     */
    hasCollectionAncestor() {
      const { element } = this.applicationContext
      const elementType = this.$registry.get('element', element.type)
      return elementType.hasCollectionAncestor(this.page, element)
    },
    /**
     * In collection element forms, the ability to view paging options
     * (e.g. items per page, or styling the load more button) is dependent
     * on whether the selected data source returns a list. When a single row
     * data source is used, we use all of its records to iterate with, so no
     * paging options are available.
     * @returns {boolean} - Whether the paging options are available.
     */
    pagingOptionsAvailable() {
      return this.selectedDataSourceReturnsList
    },
    /**
     * In collection element forms, the ability to choose a data source
     * is dependent on whether the element has a collection ancestor. If
     * it's a root-level collection element, designers can choose one,
     * otherwise only schema properties can be chosen.
     * @returns {boolean} - Whether the data source dropdown is available.
     */
    dataSourceDropdownAvailable() {
      return !this.hasCollectionAncestor
    },
    /**
     * - If the collection element is a root element:
     *     - If a non-list-type data source is selected:
     *         - Designer MUST then choose a SchemaPropertySelector to use
     *     - If a list-type data source is selected:
     *         - The SchemaPropertySelector is hidden and no longer usable.
     * - If the collection element is nested:
     *    - The data source Dropdown component is hidden and no longer usable.
     *    - The SchemaPropertySelector can choose a single property from the current_record schema.
     * @returns {boolean}
     */
    propertySelectorAvailable() {
      if (!this.hasCollectionAncestor) {
        // If we don't have a data source, or
        // We do, and it returns a list, then the schema selector isn't available.
        if (!this.selectedDataSource || this.selectedDataSourceReturnsList) {
          return false
        }
      }
      return true
    },
    /**
     * Returns all data sources that are available to the current page.
     * @returns {Array} - The data sources the page designer can choose from.
     */
    dataSources() {
      return this.$store.getters['dataSource/getPageDataSources'](
        this.page
      ).filter((dataSource) => dataSource.type)
    },
    selectedDataSource() {
      if (!this.values.data_source_id) {
        return null
      }
      return this.$store.getters['dataSource/getPageDataSourceById'](
        this.page,
        this.values.data_source_id
      )
    },
    selectedDataSourceType() {
      if (!this.selectedDataSource || !this.selectedDataSource.type) {
        return null
      }
      return this.$registry.get('service', this.selectedDataSource.type)
    },
    selectedDataSourceReturnsList() {
      return this.selectedDataSourceType?.returnsList
    },
    maxItemPerPage() {
      if (!this.selectedDataSourceType) {
        return 20
      }
      return this.selectedDataSourceType.maxResultLimit
    },
    elementHasContent() {
      const { element } = this.applicationContext
      return this.$store.getters['elementContent/getElementContent'](element)
    },
    ...mapGetters({
      element: 'element/getSelected',
    }),
  },
  watch: {
    /**
     * When the data source is changed, we need to reset the schema property
     */
    'values.data_source_id'(newValue, oldValue) {
      if (oldValue && newValue !== oldValue) {
        this.values.schema_property = null
      }
    },
    /**
     * When the array of data sources available to this page changes, ensure
     * that the selected data source is still available. If it's not, reset
     * the `data_source_id` to null`.
     */
    'dataSources.length'(newValue, oldValue) {
      if (this.values.data_source_id && oldValue > newValue) {
        if (
          !this.dataSources.some(({ id }) => id === this.values.data_source_id)
        ) {
          // Remove the data_source_id if the related dataSource has been deleted.
          this.values.data_source_id = null
        }
      }
    },
  },
}